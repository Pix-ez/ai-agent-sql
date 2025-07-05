# from data_manager import DatabaseManager
# from query_system import QueryAgent
# import os
# from dotenv import load_dotenv
# load_dotenv()
# api = os.getenv("OPENAI_API_KEY")
# def main():

#     json_file_path = "dataset.json"
    
#     # Define the desired name for your database file
#     database_file_path = "school_management.db"

#     # Initialize the manager
#     db_manager = DatabaseManager(db_path=database_file_path)
    
#     # Execute the setup process
#     # db_manager.setup_database_from_json(json_path=json_file_path)

#     my_custom_rules = [
#         "Filter by admin access using the admins table on grade, class, and region."
#     ]

#     # 3. Get the schema representation string for your LLM
#     schema_for_llm = db_manager.get_schema_representation(custom_rules=my_custom_rules)

#     # 4. Print the result
#     # print("GENERATED SCHEMA FOR LLM PROMPT:\n")
#     # print(schema_for_llm)

#     # #test query
#     query_system = QueryAgent(db_path=database_file_path, schema_for_llm=schema_for_llm)
#     print(query_system.answer_question("which student have submitted assignment yet", "ADM001"))

# if __name__ == "__main__":
#     main()

import gradio as gr
import pandas as pd
import os
from dotenv import load_dotenv
from data_manager import DatabaseManager
from query_system import QueryAgent

load_dotenv()

DATABASE_FILE_PATH = "school_management.db"
CUSTOM_RULES = [
    "Filter by admin access using the admins table on grade, class, and region."
]


def setup_db(json_file):
    """Function to be called by the Gradio button to set up the database."""
    if json_file is None:
        return "Please upload a JSON file first.", None
    
    try:
        db_manager = DatabaseManager(db_path=DATABASE_FILE_PATH)
        db_manager.setup_database_from_json(json_path=json_file.name, overwrite=True)
        
        schema_for_llm = db_manager.get_schema_representation(custom_rules=CUSTOM_RULES)
        agent = QueryAgent(db_path=DATABASE_FILE_PATH, schema_for_llm=schema_for_llm)
        
        success_message = f"✅ Database '{DATABASE_FILE_PATH}' populated successfully!"
        return success_message, agent
    except Exception as e:
        return f"❌ Error: {e}", None

def chat_interface(message, history, admin_id, agent):
    """
    The main chatbot function.
    Corrected to use `return` instead of `yield` for single, complete outputs.
    """
    if agent is None:
        error_msg = "The database has not been set up. Please go to the 'Database Setup' tab first."
        history.append((message, error_msg))
        return history  # <-- FIX: Use return

    if not admin_id:
        error_msg = "Please enter an Admin ID before asking a question."
        history.append((message, error_msg))
        return history  # <-- FIX: Use return

    try:
        response_dict = agent.answer_question(message, admin_id)
        
        answer = response_dict['answer']
        data_df = response_dict.get('data')
        if not isinstance(data_df, pd.DataFrame):
            # This case should not happen with QueryAgent, but it's a safe fallback.
            data_df = pd.DataFrame([{"error": "Received invalid data format from agent."}])

        answer = response_dict.get('answer', "No answer returned.")
        sql_query = response_dict.get('sql', "")
        
        # Build the final response string for the chatbot
        full_response = f"**Answer:** {answer}"
        if not data_df.empty and "error" not in data_df.columns:
            full_response += "\n\n**Data Found:**\n"
            full_response += data_df.to_markdown(index=False)
        if sql_query:
            full_response += f"\n\n---\n**Generated SQL:**\n```sql\n{sql_query}\n```"

        history.append((message, full_response))
        return history

    except Exception as e:
        history.append((message, f"An unexpected application error occurred: {str(e)}"))
        return history

with gr.Blocks(theme=gr.themes.Soft(), title="School Management AI Agent") as app:
    gr.Markdown("# 🏫 School Management AI Agent")
    
    # State to hold the initialized QueryAgent
    agent_state = gr.State(None)
    
    with gr.Tabs():
        with gr.TabItem("Database Setup"):
            gr.Markdown("## 1. Import Data")
            gr.Markdown("Upload your `dataset.json` file and click the button to create and populate the database.")
            
            json_uploader = gr.File(label="Upload JSON File", file_types=[".json"])
            setup_button = gr.Button("Populate Database", variant="primary")
            setup_output = gr.Textbox(label="Status", interactive=False)
            
            setup_button.click(
                fn=setup_db,
                inputs=[json_uploader],
                outputs=[setup_output, agent_state]
            )

        with gr.TabItem("AI Agent Chat"):
            gr.Markdown("## 2. Chat with your Data")
            gr.Markdown("Enter an Admin ID and ask questions about the students and school data.")
            
            admin_id_input = gr.Textbox(label="Admin ID", placeholder="e.g., ADM001")
            
            chatbot = gr.Chatbot(label="Chat History", height=400)
            
            
            with gr.Row():
                msg_input = gr.Textbox(
                    label="Your Question",
                    placeholder="e.g., Which of my students haven't submitted their assignment yet?",
                    scale=4,
                )
                send_button = gr.Button("Send", variant="primary", scale=1)

            
            def submit_message(message, history, admin_id, agent):
                # The function now returns directly, so no `next()` is needed.
                updated_history = chat_interface(message, history, admin_id, agent)
                return updated_history, ""

            send_button.click(
                submit_message,
                inputs=[msg_input, chatbot, admin_id_input, agent_state],
                outputs=[chatbot, msg_input]
            )
            msg_input.submit(
                submit_message,
                inputs=[msg_input, chatbot, admin_id_input, agent_state],
                outputs=[chatbot, msg_input]
            )


if __name__ == "__main__":
    app.launch()