# Agentic AI Building Blocks

This repository contains a series of 6 "Agentic Blocks"—modular notebooks designed to demonstrate how to build, enhance, and deploy a production-ready AI Agent using DataRobot.

The goal is to move beyond simple chatbots by equipping an agent with predictive forecasting, structured data querying, and document intelligence.

---

## Notebook Overview

### 1 - LLM Gateway
**Goal:** Establish the foundation.
* Connects to the DataRobot LLM Gateway.
* Demonstrates how to access and switch between nearly 100 different LLMs (e.g., GPT-4, Claude, Gemini) using a single secure endpoint, eliminating the need to manage individual vendor API keys.

### 2 - Advanced Data Tools
**Goal:** Give the agent "Data Analyst" capabilities.
* Uses the Model Context Protocol (MCP) to connect the agent to a DataRobot deployment acting as a data router.
* Enables the agent to autonomously query structured data warehouses (like Snowflake) to answer factual questions (e.g., "Which bakeries are we tracking?").

### 3 - Predictive Tools
**Goal:** Bridge Generative AI with Predictive AI.
* Defines a custom Tool Client that wraps a DataRobot Time Series deployment.
* Allows the agent to recognize forward-looking questions (e.g., "How many croissants will we sell next Friday?") and delegate them to a forecasting model for accurate numerical answers.

### 4 - Document Intelligence
**Goal:** Onboard unstructured knowledge (RAG).
* Integrates the Aryn SDK to intelligently parse PDF documents (e.g., Supplier Quality Standards).
* Injects this context into the agent, enabling it to answer specific compliance rules (e.g., "What is the maximum temp for butter deliveries?").

### 5 - Deploy and Evaluate
**Goal:** Move from experiment to production.
* Programmatically packages the agent code and registers it as a Custom Model in DataRobot.
* Deploys the agent to a prediction server, unlocking the Playground for user interaction and automated "LLM-as-a-Judge" evaluation metrics.

### 6 - Prompt Management
**Goal:** Decouple persona from code.
* Demonstrates how to save, version, and manage system prompts externally.
* Allows business users to update the agent's tone or instructions without requiring a code redeployment.

---

## Getting Started
1.  Open **Notebook 1** to authenticate and test your LLM connection.
2.  Proceed sequentially to build up the agent's capabilities.
3.  Ensure you have the necessary sample data (supplier_standards.pdf) uploaded for Notebook 4.