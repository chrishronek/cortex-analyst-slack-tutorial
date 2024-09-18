# Cortex Analyst Slack Bot Tutorial

This is a simple Slack bot that uses the [Cortex Analyst API](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst) to answer AdHoc analytics questions.

## Prerequisites
- A Snowflake Account
- Fact Tables in said Snowflake account
- A [semantic_model.yaml](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst/semantic-model-spec) file defining said fact tables in a Snowflake stage
- A Snowflake User with the appropriate permissions to query the fact tables and access the stage
- [Docker Desktop](https://docs.docker.com/engine/install/) installed (for running the slack app locally)
- A Slack App with:
   - The following OAuth permissions:
     - `app_mentions:read`
     - `channels:history`
     - `chat:write`
     - `files:write`
     - `groups:history`
     - `im:history`
     - `mpim:history`
   - Event Subscriptions Enabled with `app_mentions:read` as an Event Subscription
   - `connections:write` as an App-Level Token (with the token `xapp-...`)
   - Installed in your Slack workspace (with the bot user OAuth token `xoxb-...`)
   - Added to a channel in your Slack workspace

## Setup

1. Clone the repository

```bash
git clone git@github.com:chrishronek/cortex-analyst-slack-tutorial.git
```

2. Copy the `.example_env` file to `.env` and fill in the appropriate values

```bash
cp .example_env .env
```

3. Ensure Docker is running and run the following command to launch the app locally

```bash
docker-compose up --build
```

4. (Optional) Create a venv and install the dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
