"""
Streamlit application entrypoint for IncidentIQ.
Provides the user interface for inputting incident details and displaying the agent's diagnostic graph and recovery plan.
"""

import os
import pickle
import time
import streamlit as st
import pandas as pd
from typing import Dict, Any, List

from ingestion.vector_store_builder import load_all_stores
from agent.state import new_incident_state
from agent.graph import app


# 1. Page Configuration
st.set_page_config(
    layout="wide",
    page_title="IncidentIQ 🚨",
    page_icon="🚨"
)


# 2. Caching Stores and Call Graph Loading
@st.cache_resource
def get_sources_info() -> Dict[str, Any]:
    stores_path = "stores"
    call_graph_path = os.path.join(stores_path, "call_graph.pkl")
    
    info = {
        "connected": False,
        "functions_count": 0,
        "postmortems_count": 0,
        "runbooks_count": 0,
        "graph_nodes": 0,
        "graph_edges": 0,
        "stores": None,
        "call_graph": None
    }
    
    try:
        if os.path.exists(stores_path):
            stores = load_all_stores(stores_path)
            
            with open(call_graph_path, "rb") as f:
                G = pickle.load(f)
                
            info["connected"] = True
            info["stores"] = stores
            info["call_graph"] = G
            
            info["functions_count"] = stores["code_chunks"].index.ntotal
            
            all_incidents_docs = list(stores["incidents"].docstore._dict.values())
            info["postmortems_count"] = sum(1 for d in all_incidents_docs if d.metadata.get("type") == "postmortem")
            info["runbooks_count"] = sum(1 for d in all_incidents_docs if d.metadata.get("type") == "runbook")
            
            info["graph_nodes"] = len(G.nodes)
            info["graph_edges"] = len(G.edges)
    except Exception:
        pass
        
    return info


# 3. Sidebar Layout
st.sidebar.markdown("# 🚨 IncidentIQ")
st.sidebar.markdown("### AI Incident Response Intelligence")
st.sidebar.divider()

sources_info = get_sources_info()

st.sidebar.markdown("### Connected Sources")
if sources_info["connected"]:
    st.sidebar.success(f"✓ Codebase indexed ({sources_info['functions_count']} functions)")
    st.sidebar.success(f"✓ {sources_info['postmortems_count']} postmortems loaded")
    st.sidebar.success(f"✓ {sources_info['runbooks_count']} runbooks indexed")
    st.sidebar.success(f"✓ Call graph built ({sources_info['graph_nodes']} nodes, {sources_info['graph_edges']} edges)")
else:
    st.sidebar.warning(
        "⚠️ Index files not detected. Please execute `python build_stores.py` in "
        "your project directory to initialize the vector stores and call graph."
    )

st.sidebar.divider()

with st.sidebar.expander("ℹ️ How it works", expanded=False):
    st.markdown(
        """
        1. **Anonymize**: Named-entities are scrubbed from inputs using Claude.
        2. **Plan**: Formulates a diagnostic checklist for investigation.
        3. **Retrieve**: Routes checklist steps to query vector stores (FAISS).
        4. **Verify / Replan**: Verifies grounding correctness and loops back to retrieve if gaps remain.
        5. **Synthesize**: Compiles findings, maps dependency graphs, and generates a recovery report.
        """
    )


# 4. Main Area Layout
st.markdown("# Incident Response Intelligence")
st.markdown("##### Paste incident details → Agent finds root cause, past incidents, and fix")
st.divider()


# Example Inputs Config
examples = {
    "example_1": {
        "label": "Payment service 503 errors",
        "desc": "Payment service 503 errors, 40% failure rate, connection timeouts in logs",
        "logs": "TimeoutError: Could not acquire a connection from the pool within 5 seconds. DatabasePool active connections at MAX_CONNECTIONS=10."
    },
    "example_2": {
        "label": "OrderService OOM crash",
        "desc": "OrderService OOM crash, memory grew from 512MB to 4GB overnight",
        "logs": "Container OOM killed. Exit code 137. Suspected cache leak in cache_client.py."
    },
    "example_3": {
        "label": "Duplicate orders race condition",
        "desc": "Duplicate orders being created for some users, race condition suspected",
        "logs": "IntegrityError: duplicate key value violates unique constraint on (user_id, idempotency_key)."
    }
}


# Initialize Session State
if "desc_value" not in st.session_state:
    st.session_state["desc_value"] = ""
if "logs_value" not in st.session_state:
    st.session_state["logs_value"] = ""
if "final_state" not in st.session_state:
    st.session_state["final_state"] = None


with st.expander("💡 Example incidents"):
    col_ex1, col_ex2, col_ex3 = st.columns(3)
    
    if col_ex1.button(examples["example_1"]["label"], use_container_width=True):
        st.session_state["desc_value"] = examples["example_1"]["desc"]
        st.session_state["logs_value"] = examples["example_1"]["logs"]
        st.rerun()
        
    if col_ex2.button(examples["example_2"]["label"], use_container_width=True):
        st.session_state["desc_value"] = examples["example_2"]["desc"]
        st.session_state["logs_value"] = examples["example_2"]["logs"]
        st.rerun()
        
    if col_ex3.button(examples["example_3"]["label"], use_container_width=True):
        st.session_state["desc_value"] = examples["example_3"]["desc"]
        st.session_state["logs_value"] = examples["example_3"]["logs"]
        st.rerun()


# Description & Log Inputs
col_in1, col_in2 = st.columns(2)
desc_input = col_in1.text_area("Incident description", value=st.session_state["desc_value"], height=120)
logs_input = col_in2.text_area("Error logs (optional)", value=st.session_state["logs_value"], height=120)


def generate_blast_radius_dot(blast_radius: List[str], retrieved_context: List[dict], call_graph: Any) -> str:
    """
    Generates a Graphviz DOT representation of the call graph blast radius.
    Highlights source nodes in orange, and affected downstream nodes in red.
    """
    if not blast_radius:
        return "digraph G { node [style=filled]; }"
        
    dot = [
        "digraph G {",
        '  node [style=filled, fontname="Courier", fontsize=10];',
        "  rankdir=LR;",
        "  bgcolor=\"#0E1117\";",
        "  edge [color=\"#FAFAFA\"];"
    ]
    
    # 1. Discover source nodes from retrieved context (functions/methods analyzed)
    source_nodes: Set[str] = set()
    for item in retrieved_context:
        meta = item.get("metadata", {})
        cname = meta.get("class_name")
        fname = meta.get("name")
        if fname:
            node_id = f"{cname}.{fname}" if cname else fname
            source_nodes.add(node_id)
            
    # 2. Map blast radius to node IDs in the call graph
    affected_nodes: Set[str] = set()
    if call_graph:
        for node in call_graph.nodes:
            attrs = call_graph.nodes[node]
            cname = attrs.get("class_name")
            fname = attrs.get("name")
            display_name = f"{cname}.{fname}" if cname else fname
            
            # Check if this node represents an item in the blast radius list
            if any(display_name in item for item in blast_radius):
                affected_nodes.add(node)
                
    # 3. Format and color nodes
    # Source nodes = Orange
    for node in source_nodes:
        dot.append(f'  "{node}" [fillcolor="#FFC107", color="#FFC107", fontcolor="#0E1117", label="{node}"];')
        
    # Downstream affected nodes = Red
    for node in affected_nodes:
        if node not in source_nodes:
            dot.append(f'  "{node}" [fillcolor="#FF4B4B", color="#FF4B4B", fontcolor="#FAFAFA", label="{node}"];')
            
    # 4. Add dependency links from CallGraph between nodes
    if call_graph:
        for u, v in call_graph.edges:
            # Only draw edges relating to nodes we're displaying
            if (u in source_nodes or u in affected_nodes) and (v in source_nodes or v in affected_nodes):
                dot.append(f'  "{u}" -> "{v}";')
                
    dot.append("}")
    return "\n".join(dot)


if st.button("🔍 Investigate Incident", type="primary", use_container_width=True):
    if not desc_input.strip():
        st.warning("Please enter an incident description.")
    else:
        try:
            st.session_state["final_state"] = None
            
            with st.status("Analyzing incident details...", expanded=True) as status:
                # Initialize state
                current_state = new_incident_state(desc_input, logs_input or None)
                
                # Stream the state graph execution for live updates
                for event in app.stream(current_state):
                    for node_name, node_state in event.items():
                        current_state.update(node_state)
                        
                        # Fetch the latest SRE investigation trail updates
                        steps = current_state.get("investigation_steps", [])
                        if steps:
                            last_step = steps[-1]
                            status.write(f"✓ **{last_step['step']}**: {last_step['detail']} ({last_step['time']}s)")
                            
                status.update(label="Analysis complete!", state="complete")
                
            st.session_state["final_state"] = current_state
            
        except Exception as e:
            st.error(f"An error occurred during SRE investigation: {e}")


# 5. Display Results Area
final_state = st.session_state["final_state"]

if final_state:
    st.markdown("### Investigation Findings")
    
    # 4 tabs to separate report components
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Root Cause", "📚 Past Incidents", "💥 Blast Radius", "📋 Full Report"])
    
    # 🎯 Root Cause Tab
    with tab1:
        st.subheader("Diagnostic Summary")
        root_cause = final_state.get("root_cause", "No root cause generated.")
        st.error(root_cause)
        
        st.subheader("Suggested Fix")
        fix = final_state.get("suggested_fix", "No fix recommended.")
        st.code(fix, language="python")
        
    # 📚 Past Incidents Tab
    with tab2:
        st.subheader("Similar Historical Incidents")
        incidents = final_state.get("similar_incidents", [])
        if incidents:
            for idx, inc in enumerate(incidents):
                title = inc.get("title", f"Incident {idx+1}")
                summary = inc.get("summary", "No details available.")
                mttr = inc.get("mttr", "unknown")
                date = inc.get("date", "unknown")
                
                with st.expander(f"📖 {title} (Date: {date})"):
                    st.markdown(f"**MTTR**: `{mttr} min`")
                    st.write(summary)
        else:
            st.info("No similar past incidents detected.")
            
    # 💥 Blast Radius Tab
    with tab3:
        st.subheader("System Blast Radius Mapping")
        blast_radius = final_state.get("blast_radius", [])
        
        if blast_radius:
            # Display Graphviz diagram
            dot_code = generate_blast_radius_dot(
                blast_radius,
                final_state.get("retrieved_context", []),
                sources_info["call_graph"]
            )
            st.graphviz_chart(dot_code)
            
            st.markdown("#### Potentially Affected Modules:")
            for svc in blast_radius:
                st.warning(f"⚠️ {svc}")
        else:
            st.info("No blast radius calculated or no dependencies affected.")
            
    # 📋 Full Report Tab
    with tab4:
        st.subheader("Final SRE Incident Report")
        report = final_state.get("final_report", "No report generated.")
        st.markdown(report)
        
        st.download_button(
            label="📥 Download Report (.md)",
            data=report,
            file_name="sre_incident_report.md",
            mime="text/markdown"
        )
        
    # Bottom Checklist Timeline
    with st.expander("📋 Investigation Trail"):
        trail_steps = final_state.get("investigation_steps", [])
        if trail_steps:
            df = pd.DataFrame(trail_steps)
            st.table(df)
        else:
            st.info("No investigation steps recorded.")
