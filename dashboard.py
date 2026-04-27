import streamlit as st
import requests
import pandas as pd

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="AI Ticket Automation",
    page_icon="🎫",
    layout="wide",
)

st.markdown("""
<style>
.metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px;
    border-radius: 12px;
    color: white;
    text-align: center;
}
.metric-card h2 { margin: 0; font-size: 2.5em; }
.metric-card p { margin: 5px 0 0 0; font-size: 0.9em; opacity: 0.9; }
.sla-breach { background: linear-gradient(135deg, #f5365c 0%, #f56036 100%) !important; }
.open-card { background: linear-gradient(135deg, #2dce89 0%, #2dcecc 100%) !important; }
.jira-card { background: linear-gradient(135deg, #11cdef 0%, #1171ef 100%) !important; }
</style>
""", unsafe_allow_html=True)


def fetch(endpoint: str):
    try:
        resp = requests.get(f"{API_URL}{endpoint}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException:
        return None


def post(endpoint: str, data: dict):
    try:
        resp = requests.post(f"{API_URL}{endpoint}", json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


st.title("🎫 AI Ticket Automation Dashboard")

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Analytics", "📋 All Tickets", "➕ Create Ticket", "💬 Comments"
])

# ── Analytics Tab ──
with tab1:
    analytics = fetch("/analytics/summary")
    jira = fetch("/jira/status")

    if analytics:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""<div class="metric-card">
                <h2>{analytics['total_tickets']}</h2><p>Total Tickets</p>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="metric-card open-card">
                <h2>{analytics['by_status'].get('OPEN', 0)}</h2><p>Open Tickets</p>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class="metric-card sla-breach">
                <h2>{analytics['sla_breached']}</h2><p>SLA Breached</p>
            </div>""", unsafe_allow_html=True)
        with col4:
            jira_text = "Connected" if jira and jira.get("connected") else "Not Connected"
            st.markdown(f"""<div class="metric-card jira-card">
                <h2>{'✓' if jira and jira.get('connected') else '✗'}</h2><p>Jira: {jira_text}</p>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")

        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Tickets by Priority")
            priority_data = analytics.get("by_priority", {})
            if priority_data:
                df_p = pd.DataFrame(list(priority_data.items()), columns=["Priority", "Count"])
                df_p = df_p.sort_values("Priority")
                st.bar_chart(df_p.set_index("Priority"))

            st.subheader("Tickets by Type")
            type_data = analytics.get("by_type", {})
            if type_data:
                df_t = pd.DataFrame(list(type_data.items()), columns=["Type", "Count"])
                st.bar_chart(df_t.set_index("Type"))

        with col_right:
            st.subheader("Tickets by Status")
            status_data = analytics.get("by_status", {})
            if status_data:
                df_s = pd.DataFrame(list(status_data.items()), columns=["Status", "Count"])
                st.bar_chart(df_s.set_index("Status"))

            st.subheader("Tickets by Team")
            team_data = analytics.get("by_team", {})
            if team_data:
                df_tm = pd.DataFrame(list(team_data.items()), columns=["Team", "Count"])
                st.bar_chart(df_tm.set_index("Team"))

        st.subheader("Workload by Assignee")
        assignee_data = analytics.get("by_assignee", {})
        if assignee_data:
            df_a = pd.DataFrame(list(assignee_data.items()), columns=["Assignee", "Count"])
            df_a = df_a.sort_values("Count", ascending=False)
            st.bar_chart(df_a.set_index("Assignee"))
    else:
        st.error("Could not connect to API. Is the server running?")

# ── All Tickets Tab ──
with tab2:
    st.subheader("All Tickets")

    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        f_priority = st.selectbox("Priority", ["All", "P0", "P1", "P2", "P3"])
    with fcol2:
        f_status = st.selectbox("Status", ["All", "OPEN", "IN_PROGRESS", "CLOSED"])
    with fcol3:
        f_type = st.selectbox("Type", ["All", "Bug", "Feature", "Incident"])

    params = []
    if f_priority != "All":
        params.append(f"priority={f_priority}")
    if f_status != "All":
        params.append(f"status={f_status}")
    if f_type != "All":
        params.append(f"type={f_type}")
    query_str = "?" + "&".join(params) if params else ""

    tickets = fetch(f"/tickets{query_str}")

    if tickets:
        for t in tickets:
            priority_colors = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🟢"}
            p_icon = priority_colors.get(t["priority"], "⚪")

            with st.expander(
                f"{p_icon} [{t['priority']}] {t['summary']} — {t['status']}",
                expanded=False,
            ):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**Ticket ID:** `{t['ticket_id']}`")
                    st.write(f"**Type:** {t['ai_type']}")
                    st.write(f"**Priority:** {t['priority']}")
                    st.write(f"**Team:** {t['team']}")
                    st.write(f"**Assigned To:** {t.get('assigned_to', 'N/A')}")
                with col_b:
                    st.write(f"**Status:** {t['status']}")
                    st.write(f"**SLA:** {t.get('sla_hours', 'N/A')}h")
                    st.write(f"**SLA Deadline:** {t.get('sla_deadline', 'N/A')}")
                    if t.get("jira_key"):
                        st.write(f"**Jira:** [{t['jira_key']}]({t['jira_url']})")
                    if t.get("duplicate_of"):
                        st.warning(f"⚠️ Possible duplicate of: `{t['duplicate_of']}`")

                st.write("**Description:**")
                st.info(t["description"])

                if t.get("ai_fix_suggestion"):
                    st.write("**🤖 AI Fix Suggestion:**")
                    st.success(t["ai_fix_suggestion"])

                if t.get("conversation_summary"):
                    st.write("**💬 Conversation Summary:**")
                    st.info(t["conversation_summary"])

                scol1, scol2 = st.columns(2)
                with scol1:
                    new_status = st.selectbox(
                        "Update Status",
                        ["OPEN", "IN_PROGRESS", "CLOSED"],
                        key=f"status_{t['ticket_id']}",
                        index=["OPEN", "IN_PROGRESS", "CLOSED"].index(t["status"]),
                    )
                    if st.button("Update", key=f"update_{t['ticket_id']}"):
                        try:
                            resp = requests.patch(
                                f"{API_URL}/ticket/{t['ticket_id']}/status",
                                json={"status": new_status},
                                timeout=10,
                            )
                            if resp.status_code == 200:
                                st.success(f"Status updated to {new_status}")
                                st.rerun()
                        except requests.exceptions.RequestException:
                            st.error("Failed to update status")
                with scol2:
                    if st.button("🗑️ Delete", key=f"delete_{t['ticket_id']}"):
                        try:
                            resp = requests.delete(
                                f"{API_URL}/ticket/{t['ticket_id']}",
                                timeout=10,
                            )
                            if resp.status_code == 200:
                                st.success("Ticket deleted")
                                st.rerun()
                        except requests.exceptions.RequestException:
                            st.error("Failed to delete ticket")
    elif tickets is not None:
        st.info("No tickets found.")
    else:
        st.error("Could not connect to API.")

# ── Create Ticket Tab ──
with tab3:
    st.subheader("Create New Ticket")
    st.write("Describe the issue and AI will automatically classify, prioritize, and assign it.")

    description = st.text_area(
        "Ticket Description",
        height=200,
        placeholder="Describe the issue in detail...\n\nExample: The payment gateway is rejecting all credit card transactions since this morning.",
    )

    if st.button("🚀 Create Ticket", type="primary"):
        if len(description) < 10:
            st.error("Description must be at least 10 characters.")
        else:
            with st.spinner("AI is analyzing your ticket..."):
                result = post("/create-ticket", {"description": description})

            if "error" in result:
                st.error(f"Failed: {result['error']}")
            else:
                st.success("Ticket created successfully!")

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Type", result.get("ai_type", "N/A"))
                col2.metric("Priority", result.get("priority", "N/A"))
                col3.metric("Team", result.get("team", "N/A"))
                col4.metric("Assigned To", result.get("assigned_to", "N/A"))

                st.write(f"**Summary:** {result.get('summary', 'N/A')}")
                st.write(f"**SLA:** {result.get('sla_hours', 'N/A')} hours")

                if result.get("ai_fix_suggestion"):
                    st.write("**🤖 AI Fix Suggestion:**")
                    st.success(result["ai_fix_suggestion"])

                if result.get("duplicate_of"):
                    st.warning(f"⚠️ This may be a duplicate of ticket: `{result['duplicate_of']}`")

                if result.get("jira_key"):
                    st.info(f"📌 Jira Issue: [{result['jira_key']}]({result['jira_url']})")

# ── Comments Tab ──
with tab4:
    st.subheader("Ticket Comments")

    ticket_id_input = st.text_input("Enter Ticket ID")

    if ticket_id_input:
        ticket_data = fetch(f"/ticket/{ticket_id_input}")

        if ticket_data:
            st.write(f"**{ticket_data['summary']}** — {ticket_data['status']}")

            if ticket_data.get("conversation_summary"):
                st.write("**🤖 AI Conversation Summary:**")
                st.info(ticket_data["conversation_summary"])

            comments = ticket_data.get("comments") or []
            if comments:
                for c in comments:
                    st.markdown(f"**{c['author']}** ({c['created_at'][:19]})")
                    st.write(c["text"])
                    st.markdown("---")
            else:
                st.info("No comments yet.")

            st.write("**Add Comment:**")
            author = st.text_input("Your Name", key="comment_author")
            comment_text = st.text_area("Comment", key="comment_text")

            if st.button("💬 Add Comment"):
                if author and comment_text:
                    result = post(
                        f"/ticket/{ticket_id_input}/comment",
                        {"author": author, "text": comment_text},
                    )
                    if "error" not in result:
                        st.success("Comment added!")
                        st.rerun()
                    else:
                        st.error("Failed to add comment")
                else:
                    st.error("Both name and comment are required.")
        else:
            st.error("Ticket not found. Check the ID.")
