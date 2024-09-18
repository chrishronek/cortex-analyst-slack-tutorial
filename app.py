import os
import logging
from slack_bolt import App
from io import StringIO
from slack_bolt.adapter.socket_mode import SocketModeHandler
import snowflake.connector
import requests

# Environment variables
SNOWFLAKE_VARS = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    "database": os.getenv("SNOWFLAKE_DATABASE"),
    "schema": os.getenv("SNOWFLAKE_SCHEMA"),
    "role": os.getenv("SNOWFLAKE_ROLE"),
    "stage": os.getenv("SNOWFLAKE_STAGE"),
}
SEMANTIC_FILE = os.getenv("SEMANTIC_FILE")

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

def send_message(prompt: str, conn):
    request_body = {
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        "semantic_model_file": f"@{SNOWFLAKE_VARS['database']}.{SNOWFLAKE_VARS['schema']}.{SNOWFLAKE_VARS['stage']}/{SEMANTIC_FILE}",
    }
    
    resp = requests.post(
        url=f"https://{SNOWFLAKE_VARS['account']}.snowflakecomputing.com/api/v2/cortex/analyst/message",
        json=request_body,
        headers={
            "Authorization": f'Snowflake Token="{conn.rest.token}"',
            "Content-Type": "application/json",
        },
    )
    if resp.status_code < 400:
        return resp.json()
    else:
        raise Exception(f"Failed request with status {resp.status_code}: {resp.text}")
    
def generate_summary(prompt: str, sql_query: str,data_for_summary: str, conn) -> str:
    """Generate a summary of the metric output by the bot."""
    prompt = f"""
    You have been answering questions in a slack thread as a slackbot. Your purpose as a slackbot is to retrieve data from our snowflake data warehouse.
    You've already retrieved data from the warehouse based on the user's question. The user has asked you to provide a summary of the data you've retrieved.
    Based on the generated content between the <content> tags, provide a summary of the data you've retrieved. The summary should be concise and should
    make it easy for the user to understand the key insights from the data. Don't include anything else except for the summary text in your response (no headers).

    <prompt>
    {prompt}
    </prompt>

    <sql_query>
    {sql_query}
    </sql_query>
    
    <data_results>
    {data_for_summary}
    </data_results>
    """

    try:
        cmd = "select snowflake.cortex.complete(%s, %s) as response"
        cursor = conn.cursor()
        
        logging.info(f"Executing SQL command: {cmd}")
        logging.info(f"Model parameter: llama3.1-405b")
        logging.info(f"Prompt parameter: {prompt[:100]}...")  # Log first 100 characters of prompt
        
        cursor.execute(cmd, ("llama3.1-405b", prompt))
        
        logging.info("SQL execution successful. Fetching result...")
        result = cursor.fetchone()
        cursor.close()

        return result[0].strip() if result and result[0] else ""
    
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}", exc_info=True)
        return ""

@app.event("app_mention")
def handle_mention(event, say):
    user = event['user']
    text = event['text']
    thread_ts = event.get('thread_ts', None) or event['ts']
    
    logger.info(f"Received mention from user {user}")
    
    try:
        conn = snowflake.connector.connect(**SNOWFLAKE_VARS)
        question = text.split(">", 1)[1].strip() if ">" in text else text
        
        response = send_message(prompt=question, conn=conn)
        content = response["message"]["content"]
        
        output = []
        sql_query = ""
        
        for item in content:
            if item["type"] == "text":
                output.append(item["text"])
            elif item["type"] == "sql":
                sql_query = item["statement"]
        
        # Combine the output and SQL query
        full_output = "\n".join(output)
        if sql_query:
            with conn.cursor() as cur:
                cur.execute(sql_query)
                df = cur.fetch_pandas_all()

            if not df.empty:
                csv_buffer = StringIO()
                df.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                
                data_for_summary = "Resulting Data:\n" + df.to_string(index=False)
                summary = generate_summary(prompt=question, sql_query=sql_query, data_for_summary=data_for_summary, conn=conn)

            full_output += f"\n\nSQL Query:\n```sql\n{sql_query}\n```\n\nSummary:\n{summary}"

        say(text=full_output, thread_ts=thread_ts)
        logger.info("Response sent successfully")
    except Exception as e:
        logger.error(f"Error processing mention: {str(e)}", exc_info=True)
        say(text="Sorry, I encountered an error. Please try again later.", thread_ts=thread_ts)

if __name__ == "__main__":
    logger.info("Starting the Slack bot")
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()