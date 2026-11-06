"""Streamlit customer support dashboard, backed exclusively by the HTTP API."""

from pathlib import Path
from html import escape
import hmac
import os
import sys

# Streamlit also supports running this file directly from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from app.client import APIError, SupportAPI


def require_access():
    expected = os.environ.get("SUPPORT_DASHBOARD_PASSWORD")
    if not expected or st.session_state.get("access_granted"):
        return True

    def check_password():
        supplied = st.session_state.get("access_password", "")
        st.session_state["access_granted"] = hmac.compare_digest(supplied.encode(), expected.encode())
        st.session_state["access_failed"] = not st.session_state["access_granted"]
        if st.session_state["access_granted"]:
            del st.session_state["access_password"]

    st.title("Support Desk")
    st.caption("Sign in to the reviewer workspace.")
    with st.form("workspace_access"):
        st.text_input("Workspace password", type="password", key="access_password")
        st.form_submit_button("Sign in", on_click=check_password, type="primary")
    if st.session_state.get("access_failed"):
        st.error("Password not recognized.")
    return False


def render_html(markup):
    st.markdown(markup, unsafe_allow_html=True)


def readable(value):
    return value.replace("_", " ").title()


def navigate_to_review(ticket_id):
    st.session_state["navigation"] = "Ticket review"
    st.session_state["requested_ticket"] = ticket_id
    st.session_state["review_filter"] = "All tickets"
    st.session_state["ticket_page"] = 1
    st.session_state['category_filter'] = 'All categories'
    st.session_state['priority_filter'] = 'All priorities'
    st.session_state['ticket_search'] = ''


def navigate_to_new():
    st.session_state["navigation"] = "New ticket"


def reset_review_page():
    st.session_state["ticket_page"] = 1


def show_result(ticket):
    result = ticket["result"]
    prediction = result["prediction"]
    with st.container(border=True):
        st.subheader(readable(prediction["intent"]))
        a, b, c = st.columns(3)
        a.metric("Department", result["department"])
        b.metric("Priority", result["priority"])
        c.metric("Model score", f"{prediction['score']:.3f}")
        st.caption("Model scores are uncalibrated. Priority and department follow configured business rules.")
        if ticket["review_status"] == "reviewed":
            st.success("Reviewed · original prediction preserved below")
        elif result["requires_review"]:
            st.warning("Human review needed · " + ", ".join(readable(reason) for reason in result["review_reasons"]))
        else:
            st.info("Routed · no review requested by the current policy")
        with st.expander("Decision details"):
            st.write({"Category": prediction["category"], "Priority reason": readable(result["priority_reason"]),
                      "Routing reason": readable(result["routing_reason"]), "Model version": prediction["model_version"],
                      "Policy version": result["policy_version"], "Inference and routing (ms)": result["latency_ms"]})


def show_overview(api):
    st.title("Support overview")
    st.caption("A clear view of ticket volume, routing and the human review queue.")
    metrics = api.analytics()
    columns = st.columns(4)
    for column, label, key in zip(columns, ["Total tickets", "Awaiting review", "Reviewed tickets", "Feedback entries"],
                                ["tickets", "pending_review", "reviewed_tickets", "feedback_entries"]):
        with column:
            st.metric(label, metrics[key], border=True)
    if metrics["tickets"] == 0:
        st.info("Your workspace is ready. Submit a ticket to see predictions, routing and review activity here.")
        st.button("Create your first ticket", type="primary", on_click=navigate_to_new)
        return
    left, right = st.columns(2)
    with left:
        departments = metrics["original_departments"]
        maximum = max(departments.values(), default=1) or 1
        bars = ''.join(f'<div class="department-column"><span>{count}</span><div class="department-bar" style="height:{max(2, count / maximum * 190)}px"></div><small>{escape(name)}</small></div>' for name, count in departments.items())
        render_html(f'<section class="chart-card"><h3>Routing by department</h3><div class="department-chart">{bars}</div></section>')
    with right:
        counts = {priority: metrics["original_priorities"].get(priority, 0) for priority in ["Critical", "High", "Medium", "Low"]}
        maximum = max(counts.values(), default=1) or 1
        rows = ''.join(f'<div class="priority-row"><span>{priority}</span><div class="priority-track"><div class="priority-fill {priority.lower()}" style="width:{count / maximum * 100}%"></div></div><strong>{count}</strong></div>' for priority, count in counts.items())
        render_html(f'<section class="chart-card"><h3>Priority distribution</h3><div class="priority-chart">{rows}</div><p class="chart-note">Charts show original routing decisions. Corrections are retained in each ticket&#9633;s review history.</p></section>')
    search = st.session_state.get('overview_search', '').strip().casefold()
    result = api.tickets(limit=100 if search else 5)
    tickets = result['items']
    if search:
        tickets = [t for t in tickets if search in ' '.join([t['id'], t['text'], readable(t['result']['prediction']['intent']), t['result']['department']]).casefold()]
        st.caption('Search covers the latest 100 tickets: messages, intents, departments and ticket IDs.')
    with st.container(border=True):
        heading, count = st.columns([5, 1])
        heading.subheader('Recent tickets' if not search else 'Search results')
        count.caption(f"{len(tickets)} of {result['total']}")
        show_ticket_table(tickets)
    with st.expander('Human feedback analytics'):
        st.metric('Human correction rate', f"{metrics['correction_rate']:.1%}")
        st.caption('Latest review per ticket; confirmations are not corrections. This is review activity, not unbiased test accuracy.')
        if metrics['corrected_intents']:
            st.bar_chart(pd.DataFrame.from_dict(metrics['corrected_intents'], orient='index', columns=['Corrected tickets']))
        if metrics['review_activity_by_day']:
            st.dataframe(pd.DataFrame.from_dict(metrics['review_activity_by_day'], orient='index').rename_axis('Review date'), width='stretch')


def show_new_ticket(api):
    st.title("New support ticket")
    st.caption("Submit a customer message to classify the intent, set a priority and choose a department.")
    left, right = st.columns([2, 1])
    with left:
        with st.form("new_ticket_form"):
            text = st.text_area("Customer message", height=190, max_chars=10000, key="ticket_text",
                                placeholder="For example: I requested a refund last week. Can you check its status&#9633;")
            submitted = st.form_submit_button("Classify and save ticket", type="primary")
        if submitted:
            if not text.strip():
                st.error("Enter a customer message before submitting.")
            else:
                with st.spinner("Classifying and routing your ticket…"):
                    st.session_state["latest_ticket"] = api.create_ticket(text)
                st.success("Ticket saved")
    with right:
        with st.container(border=True):
            st.subheader("What happens next")
            st.write("1. The model predicts the customer’s intent.\n2. Business rules choose priority and department.\n3. Uncertain or escalated cases enter human review.")
            st.caption("Messages and feedback are saved in the workspace database. Avoid adding unnecessary personal information.")
    ticket = st.session_state.get("latest_ticket")
    if ticket:
        ticket = api.ticket(ticket["id"])
        st.subheader("Most recently submitted")
        st.caption(f"Ticket {ticket['id']} · {ticket['created_at']}")
        show_result(ticket)
        st.button("Open ticket review", on_click=navigate_to_review, args=(ticket["id"],))


def show_ticket_table(tickets):
    if not tickets:
        st.info("No tickets to display.")
        return
    rows = []
    for ticket in tickets:
        result = ticket['result']
        priority = result['priority']
        status = ticket['review_status']
        cells = [f'<code>{escape(ticket["id"][:8])}</code>', escape(ticket['text']),
                 escape(readable(result['prediction']['intent'])), escape(result['department']),
                 f'<span class="badge {escape(priority.lower())}">{escape(priority)}</span>',
                 f'<span class="badge {escape(status)}">{escape(readable(status))}</span>']
        rows.append('<tr>' + ''.join(f'<td>{cell}</td>' for cell in cells) + '</tr>')
    headers = ''.join(f'<th>{name}</th>' for name in ['Ticket', 'Message', 'Intent', 'Department', 'Priority', 'Review'])
    render_html('<div class="ticket-table-wrap"><table class="ticket-table"><thead><tr>' + headers + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')



def show_review(api):
    st.title("Ticket review")
    st.caption("Inspect the original prediction, record a correction or confirm the existing intent.")
    choice = st.selectbox("Show", ["Awaiting review", "All tickets", "No outstanding review"], key="review_filter", on_change=reset_review_page)
    taxonomy = api.taxonomy()
    a, b = st.columns(2)
    category = a.selectbox('Category', ['All categories'] + sorted({item['category'] for item in taxonomy['intents'].values()}), key='category_filter', on_change=reset_review_page)
    priority = b.selectbox('Priority', ['All priorities'] + taxonomy['priorities'], key='priority_filter', on_change=reset_review_page)
    search = st.text_input('Search messages', max_chars=200, key='ticket_search', on_change=reset_review_page)
    page = int(st.number_input("Page", min_value=1, step=1, key="ticket_page"))
    needs_review = {"Awaiting review": True, "All tickets": None, "No outstanding review": False}[choice]
    result = api.tickets(limit=20, offset=(page - 1) * 20, needs_review=needs_review,
                         category=None if category == 'All categories' else category,
                         priority=None if priority == 'All priorities' else priority, search=search)
    st.caption(f"{result['total']} matching tickets · 20 per page")
    tickets = result["items"]
    if not tickets:
        st.info("No tickets on this page. Change the filter or return to page 1.")
        return
    show_ticket_table(tickets)
    lookup = {ticket["id"]: ticket for ticket in tickets}
    requested = st.session_state.pop("requested_ticket", None)
    if requested in lookup:
        st.session_state["selected_ticket"] = requested
    if st.session_state.get("selected_ticket") not in lookup:
        st.session_state["selected_ticket"] = tickets[0]["id"]
    selected = st.selectbox("Select a ticket", list(lookup), format_func=lambda identifier: f"{identifier[:8]} · {lookup[identifier]['text'][:70]}", key="selected_ticket")
    ticket = api.ticket(selected)
    st.subheader("Customer message")
    st.text(ticket["text"])
    st.caption(f"Created {ticket['created_at']} · Ticket {selected}")
    show_result(ticket)
    taxonomy = api.taxonomy()
    labels = sorted(taxonomy["intents"])
    original = ticket["result"]["prediction"]["intent"]
    st.subheader("Human feedback")
    st.caption("A confirmation can keep the original intent. Feedback preserves the original result and does not retrain the model.")
    with st.form(f"feedback_form_{selected}"):
        intent = st.selectbox("Reviewed intent", labels, index=labels.index(original), format_func=readable, key=f"intent_{selected}")
        a, b = st.columns(2)
        priority = a.selectbox("Priority correction", ["Keep original"] + taxonomy["priorities"], key=f"priority_{selected}")
        department = b.selectbox("Department correction", ["Keep original"] + taxonomy["departments"], key=f"department_{selected}")
        note = st.text_area("Review note (optional)", max_chars=2000, key=f"note_{selected}")
        reviewer = st.text_input("Reviewer label (optional)", max_chars=80, key=f"reviewer_{selected}")
        submitted = st.form_submit_button("Save review", type="primary")
    if submitted:
        values = {"corrected_intent": intent, "note": note}
        if priority != "Keep original":
            values["corrected_priority"] = priority
        if department != "Keep original":
            values["corrected_department"] = department
        if reviewer.strip():
            values["reviewer"] = reviewer.strip()
        api.add_feedback(selected, values)
        st.session_state["review_saved"] = selected
        st.rerun()
    st.subheader("Review history")
    history = api.feedback(selected)
    if not history:
        st.info("No feedback recorded yet.")
    for item in reversed(history):
        with st.container(border=True):
            st.markdown(f"**{readable(item['corrected_intent'])}** · {item['corrected_category']}")
            st.caption(f"{item['created_at']} · {item['reviewer'] or 'Unlabelled reviewer'}")
            if item["corrected_priority"] or item["corrected_department"]:
                st.write({"Priority correction": item["corrected_priority"] or "Unchanged", "Department correction": item["corrected_department"] or "Unchanged"})
            if item["note"]:
                st.text(item["note"])
            st.caption("Pending training-data approval")


def main():
    st.set_page_config(page_title="Support Desk · Ticket intelligence", page_icon="📬", layout="wide")
    render_html((Path(__file__).parent / "dashboard.css").read_text(encoding="utf-8"))
    if not require_access():
        st.stop()
    api = SupportAPI()
    with st.sidebar:
        render_html('<div class="brand"><span class="brand-icon">&#9633;</span><div><strong>Support Desk</strong><small>TICKET INTELLIGENCE</small></div></div>')
        page = st.radio("Workspace", ["Overview", "New ticket", "Ticket review"], key="navigation", label_visibility="collapsed")
        st.divider()
        refresh = st.button("Refresh workspace", width="stretch")
        st.caption("Reviewer workspace · human review enabled")
    if refresh:
        st.rerun()
    try:
        health = api.health()
        with st.sidebar:
            st.success("API connected")
            with st.expander("Workspace details"):
                st.caption(f"Model: {health['model_version']}")
                st.caption(f"Policy: {health['policy_version']}")
                st.caption(f"Application: {health.get('application_version', '1.0.0')}")
        search_column, action_column = st.columns([4, 1])
        with search_column:
            st.text_input("Search tickets, intents, departments", placeholder="Search tickets, intents, departments", key="overview_search", label_visibility="collapsed", disabled=page != "Overview")
        with action_column:
            st.button("+ New ticket", type="primary", on_click=navigate_to_new, width="stretch")
        if st.session_state.pop("review_saved", None):
            st.success("Review saved. The original prediction is preserved and the review queue is updated.")
        {"Overview": show_overview, "New ticket": show_new_ticket, "Ticket review": show_review}[page](api)
    except APIError as error:
        st.error(str(error))
        st.info("Start the backend with the project’s API run command, then use Refresh workspace.")


if __name__ == "__main__":
    main()
