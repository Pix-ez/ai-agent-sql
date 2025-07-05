
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
import traceback
import sqlite3
import json
import os
import pandas as pd

template="""
        You are an expert SQLite analyst. Convert the natural language query to a valid SQLite statement.

        {schema}

        ---
        CRITICAL RULES:
        1.  **MANDATORY ADMIN FILTER**: You MUST filter the students or related data based on the admin's access rights. The main `FROM` clause **must** join `students` with the `admins` table on their shared `grade`, `class`, and `region`. The query must then be filtered with `WHERE admins.id = '{admin_id}'`. This is the most important rule.

        2.  **FINDING NON-EXISTENT DATA (Exclusion)**: To find items that do NOT have an entry in another table (e.g., students who have not submitted), the most reliable method is a `WHERE ... NOT IN (SELECT ...)` subquery.
        
        3.  **UNIQUE ALIASES**: When joining multiple tables, you MUST give each table a unique and simple alias to avoid ambiguity. For example: `FROM students s JOIN admins adm JOIN assignments asg`. **Never use the same alias for different tables.**
        ---
        **COMPLEX EXAMPLE (How to combine rules):**
        This is how to correctly find students who haven't submitted an assignment, WHILE respecting the admin's access:

        Natural Language Query: "Which of my students have not submitted their work?"
        Admin ID: "ADM001"

        Correct SQL:
        ```sql
        SELECT s.* FROM students s JOIN admins a ON s.grade = a.grade AND s.class = a.class AND s.region = a.region WHERE a.id = 'ADM001' AND s.id NOT IN (SELECT student_id FROM submissions WHERE submitted = 1)
        ```
        This example correctly joins `students` and `admins` first and then applies the `NOT IN` filter. Follow this pattern.

        ---
        Natural Language Query: "{query}"
        
        Return only a single, valid SELECT statement.
        """

class ResponseSchemaSQL(BaseModel):
    """Schema for sql response"""
    sql_query: str = Field(description="The generated SQL query.")
   
class QueryAgent:
    def __init__(self, db_path="school_management.db", schema_for_llm=None):
        self.db_path = db_path
        self.schema_for_llm = schema_for_llm
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        
    
    def query_to_sql_chain(self, natural_query: str, admin_id: int, schema: str):
        """Convert a natural language query into a SQL statement using LangChain + OpenAI"""
        
        prompt = PromptTemplate(
            input_variables=["query", "admin_id", "schema"],
            template=template
            # template="""
            # You are a SQL expert. Convert this natural language query to SQL based on the provided schema and rules.
            
            # Database Schema:
            # {schema}
            
            # Important Rules:
            # 1.  Admin Access: Always filter results by the admin's scope. Join with the `admin_access` table WHERE `admin_access.admin_id` = '{admin_id}'.
            # 2.  Finding Non-Existent Data: To find items that do NOT have an entry in another table (e.g., students who have not submitted an assignment), use a `WHERE ... NOT IN (SELECT ...)` subquery. This is the most reliable method.
            #     - Correct Example (Find students who haven't submitted A001):
            #     `SELECT * FROM students WHERE id NOT IN (SELECT student_id FROM submissions WHERE assignment_id = 'A001' AND submitted = 1)`
            # 3.  Avoid the LEFT JOIN Trap: Do not use `LEFT JOIN` and then filter on the right table's columns in the `WHERE` clause (e.g., `WHERE right_table.column = 'value'`). This is incorrect. Use the `NOT IN` pattern instead.
            # 4.  Dates: Use standard SQLite date functions like `date('now')` for date comparisons.
            # 5.  Output: Return only a single, valid SELECT statement. Do not provide any explanation.

            # Natural Language Query: "{query}"
            
            # You must output your response in the correct JSON format. Do not include any other text or explanation.
            # """
        )

        
        # This will now work because 'llm' is an instance of the new ChatOpenAI class
        structured_llm = self.llm.with_structured_output(ResponseSchemaSQL)
        
        # Create the chain using LangChain Expression Language (LCEL)
        chain = prompt | structured_llm

        # Invoke the chain with the input dictionary
        result = chain.invoke({
            "query": natural_query,
            "admin_id": admin_id,
            "schema": schema
        })

        return result.sql_query.strip()
    
    def execute_query(self, sql_query):
        """Execute SQL query safely"""
        try:
            # Basic SQL injection prevention
            if not sql_query.strip().upper().startswith('SELECT'):
                return {"error": "Only SELECT queries are allowed"}
            
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(sql_query, conn)
            conn.close()
            
            return {
                "success": True,
                "data": df.to_dict('records'),
                "count": len(df)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    
    def answer_question(self, question, admin_id):
        """Answer a user query by generating SQL, retrieving data, and using LLM for final answer generation"""
        try:
            # Step 1: Convert NL to SQL
            sql_query = self.query_to_sql_chain(natural_query=question, 
                                                admin_id=admin_id, 
                                                schema= self.schema_for_llm)
            print(f"Generated SQL: {sql_query}")
            
            # Step 2: Execute SQL
            result = self.execute_query(sql_query)

            if not result.get("success"):
                return {
                    "answer": f"Sorry, I couldn't process your query: {result.get('error')}",
                    "error": result.get('error')
                }

            data = result["data"]
            print(f'output data: {data}')
            # Step 3: Generate final answer via LLM
            prompt = PromptTemplate(
                input_variables=["question", "data"],
                template="""
                You are an AI assistant. Use the structured data it's from database it has the answer to user's query. Just convert the data into proper answer.
                
                User Question: "{question}"
                
                Data (from SQL):
                {data}
                
                Respond clearly and concisely based on the data. Avoid speculation. If data is missing or empty, say so.
                """
            )

            chain = prompt | self.llm

            response = chain.invoke({
                "question": question,
                "data": str(data)
            })
            

            return {
                "answer": response.content.strip(),
                "data": data,
                "sql": sql_query
            }

        except Exception as e:
            print(traceback.format_exc())
            return {
                "answer": f"Sorry, something went wrong: {str(e)}",
                "error": str(e)
            }