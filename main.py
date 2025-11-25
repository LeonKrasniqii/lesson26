import streamlit as st
import requests
import threading
import time
import uvicorn
import os
from dotenv import load_dotenv
from app import app

load_dotenv()

API_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# Run API server in background
def run_api():
    uvicorn.run(app, host="127.0.0.1", port=8000)

thread = threading.Thread(target=run_api, daemon=True)
thread.start()
time.sleep(1)

st.title("Task Manager App")

# Helper functions
def get_tasks():
    res = requests.get(f"{API_URL}/tasks/")
    return res.json() if res.status_code == 200 else []

def add_task(title, description):
    requests.post(f"{API_URL}/tasks/", json={"title": title, "description": description})

def update_task(task_id, completed):
    requests.put(f"{API_URL}/tasks/{task_id}", params={"completed": completed})

def delete_task(task_id):
    requests.delete(f"{API_URL}/tasks/{task_id}")

# Sidebar Menu
menu = st.sidebar.selectbox(
    "Navigation",
    ["Dashboard", "Manage Tasks", "Settings"]
)

# Dashboard
if menu == "Dashboard":
    st.header("Dashboard Overview")

    tasks = get_tasks()
    st.subheader("All Tasks")
    st.dataframe(tasks)

# Manage Tasks
elif menu == "Manage Tasks":
    st.header("Manage Tasks")

    st.subheader("Add Task")
    with st.form("add_task"):
        title = st.text_input("Title")
        desc = st.text_input("Description")
        if st.form_submit_button("Add Task"):
            if title:
                add_task(title, desc)
                st.rerun()
            else:
                st.warning("Title is required")

    st.subheader("Existing Tasks")
    tasks = get_tasks()
    for task in tasks:
        col1, col2, col3, col4 = st.columns([3,4,2,2])

        col1.write(task["title"])
        col2.write(task["description"])

        chk = col3.checkbox("Completed", value=task["completed"], key=f"ck{task['id']}")
        if chk != task["completed"]:
            update_task(task["id"], chk)
            st.rerun()

        if col4.button("Delete", key=f"del{task['id']}"):
            delete_task(task["id"])
            st.rerun()

# Settings Page
elif menu == "Settings":
    st.header("Settings")
    st.write("Additional configuration options will appear here.")
