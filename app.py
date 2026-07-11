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
from streamlit_oauth import OAuth2Component
from agent.auth_db import init_user_db, register_user, get_registered_users


# 1. Page Configuration
st.set_page_config(
    layout="wide",
    page_title="IncidentIQ 🚨",
    page_icon="🚨"
)

# Initialize User Database
init_user_db()

# Google OAuth Setup
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

is_google_configured = (
    CLIENT_ID 
    and CLIENT_SECRET 
    and "your-google-client-id" not in CLIENT_ID 
    and "your-google-client-secret" not in CLIENT_SECRET
)

# Authentication Screening
if "auth" not in st.session_state:
    st.markdown("<h1 style='text-align: center; color: #FF4B4B; margin-top: 50px;'>🚨 IncidentIQ</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>AI Incident Response Intelligence</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #FAFAFA;'>Log in to analyze system blast radius, query vector databases, and synthesize SRE reports.</p>", unsafe_allow_html=True)
    st.divider()

    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        st.markdown("<h4 style='color: #FF4B4B;'>🔑 Google Single Sign-On</h4>", unsafe_allow_html=True)
        if is_google_configured:
            oauth2 = OAuth2Component(
                CLIENT_ID,
                CLIENT_SECRET,
                "https://accounts.google.com/o/oauth2/v2/auth",
                "https://oauth2.googleapis.com/token",
                "https://oauth2.googleapis.com/token",
                "https://accounts.google.com/o/oauth2/v2/auth"
            )
            result = oauth2.authorize_button(
                name="Sign in with Google",
                redirect_uri="http://localhost:8501",
                scope="openid email profile",
                key="google_login"
            )
            if result and "token" in result:
                st.session_state["auth"] = result["token"]
                user_info = result["token"].get("id_token_decoded", {})
                register_user(
                    email=user_info.get("email", ""),
                    name=user_info.get("name", "Google User"),
                    picture=user_info.get("picture", "")
                )
                st.rerun()
        else:
            st.info("Google Sign-In is not configured in `.env`. Run in Developer/Guest mode on the right.")
            
    with col_btn2:
        st.markdown("<h4 style='color: #FF4B4B;'>🛠️ Developer / Guest Access</h4>", unsafe_allow_html=True)
        guest_name = st.text_input("Enter your name", value="Guest SRE")
        guest_email = st.text_input("Enter your email", value="guest@example.com")
        if st.button("Login as Guest / Developer", use_container_width=True):
            st.session_state["auth"] = {
                "user_type": "guest",
                "email": guest_email,
                "name": guest_name,
                "picture": ""
            }
            register_user(email=guest_email, name=guest_name, picture="")
            st.rerun()
            
    st.stop()


# Get Active User Details
auth_data = st.session_state["auth"]
if auth_data.get("user_type") == "guest":
    user_email = auth_data.get("email", "guest@example.com")
    user_name = auth_data.get("name", "Guest SRE")
    user_picture = ""
else:
    user_info = auth_data.get("id_token_decoded", {})
    user_email = user_info.get("email", "")
    user_name = user_info.get("name", "Google User")
    user_picture = user_info.get("picture", "")


# Initialize cache-busting session state
if "cache_key" not in st.session_state:
    st.session_state["cache_key"] = 0

# 2. Caching Stores and Call Graph Loading
@st.cache_resource
def get_sources_info(cache_key: int = 0) -> Dict[str, Any]:
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

# Render User Profile Card
st.sidebar.markdown("### User Profile")
col_p1, col_p2 = st.sidebar.columns([1, 4])
with col_p1:
    if user_picture:
        st.image(user_picture, width=45)
    else:
        st.markdown("<h2 style='margin: 0;'>👤</h2>", unsafe_allow_html=True)
with col_p2:
    st.markdown(f"**{user_name}**  \n`{user_email}`")
if st.sidebar.button("Logout", use_container_width=True):
    del st.session_state["auth"]
    st.rerun()

st.sidebar.divider()

# Registered SRE Team list
with st.sidebar.expander("👥 Registered SRE Team"):
    registered_users = get_registered_users()
    if registered_users:
        for name, email, pic, last_login in registered_users:
            col_u1, col_u2 = st.columns([1, 4])
            with col_u1:
                if pic:
                    st.image(pic, width=24)
                else:
                    st.markdown("👤")
            with col_u2:
                st.markdown(f"**{name}**  \n`{email}`")
            st.divider()
    else:
        st.write("No team members registered.")

st.sidebar.divider()

sources_info = get_sources_info(st.session_state["cache_key"])

st.sidebar.markdown("### Connected Sources")
if sources_info["connected"]:
    st.sidebar.success(f"✓ Codebase indexed ({sources_info['functions_count']} functions)")
    st.sidebar.success(f"✓ {sources_info['postmortems_count']} postmortems loaded")
    st.sidebar.success(f"✓ {sources_info['runbooks_count']} runbooks indexed")
    st.sidebar.success(f"✓ Call graph built ({sources_info['graph_nodes']} nodes, {sources_info['graph_edges']} edges)")
else:
    st.sidebar.warning(
        "⚠️ Index files not detected. Import a repository or execute "
        "`python build_stores.py` in your project directory."
    )

st.sidebar.divider()

# Git Repository Import Panel
st.sidebar.markdown("### 📥 Import Codebase from GitHub")
repo_url = st.sidebar.text_input("GitHub Repo URL", placeholder="https://github.com/...")
repo_branch = st.sidebar.text_input("Branch Name", value="main")

if st.sidebar.button("Clone & Index Codebase", use_container_width=True):
    if not repo_url.strip():
        st.sidebar.error("Please enter a valid Git Repository URL.")
    else:
        with st.sidebar.status("Cloning repository...", expanded=True) as status:
            try:
                import git
                import shutil
                
                base_dir = os.path.dirname(os.path.abspath(__file__))
                sample_codebase_dir = os.path.join(base_dir, "data", "sample_codebase")
                
                # Remove existing directory to ensure a clean clone
                if os.path.exists(sample_codebase_dir):
                    shutil.rmtree(sample_codebase_dir)
                os.makedirs(sample_codebase_dir, exist_ok=True)
                
                status.write(f"Cloning {repo_url} (branch: {repo_branch}) [shallow clone]...")
                git.Repo.clone_from(repo_url, sample_codebase_dir, branch=repo_branch, depth=1)
                status.write("✓ Repository cloned successfully.")
                
                # Rebuild stores and dependency graphs programmatically
                status.write("Rebuilding Code Chunks Vector Store...")
                from ingestion.ast_chunker import chunk_directory
                from ingestion.vector_store_builder import build_code_chunks_store, build_summaries_store
                from ingestion.call_graph import build_call_graph
                
                code_docs = chunk_directory(sample_codebase_dir)
                status.write(f"✓ AST chunking generated {len(code_docs)} chunks.")
                
                stores_dir = os.path.join(base_dir, "stores")
                os.makedirs(stores_dir, exist_ok=True)
                
                code_chunks_path = os.path.join(stores_dir, "code_chunks")
                build_code_chunks_store(code_docs, code_chunks_path)
                status.write("✓ Code Chunks Vector Store updated.")
                
                status.write("Rebuilding Call Graph...")
                G = build_call_graph(sample_codebase_dir)
                call_graph_path = os.path.join(stores_dir, "call_graph.pkl")
                with open(call_graph_path, "wb") as f:
                    pickle.dump(G, f)
                status.write(f"✓ Call Graph updated ({len(G.nodes)} nodes).")
                
                status.write("Generating summaries...")
                summaries_path = os.path.join(stores_dir, "summaries")
                build_summaries_store(sample_codebase_dir, summaries_path)
                status.write("✓ Summaries Vector Store updated.")
                
                # Bust the cache to update sidebar info
                st.session_state["cache_key"] += 1
                
                status.update(label="Repository Indexed Successfully!", state="complete")
                st.sidebar.success("Index updated! Reloading sources...")
                time.sleep(1.5)
                st.rerun()
                
            except Exception as e:
                status.update(label="Indexing failed!", state="error")
                st.sidebar.error(f"Error: {e}")

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
