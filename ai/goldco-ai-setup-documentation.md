# Goldco AI System - Setup Documentation

## What We Built

A self-hosted RAG (Retrieval Augmented Generation) system running on your Hostinger VPS that lets you query company data using AI. The system:

- Stores company documents/data in a vector database (ChromaDB)
- Uses local LLMs (via Ollama) to analyze and answer questions
- Has a FastAPI wrapper connecting everything
- Runs entirely in Docker containers

## Server Details

**VPS:** Hostinger VPS
**Location:** `/docker/goldco-ai/`
**Resources:**
- 2 CPU cores
- 8GB RAM (currently using ~6GB when model is loaded)
- 100GB disk (currently using ~23GB)

## System Architecture

```
┌─────────────┐
│   You       │
└──────┬──────┘
       │ HTTP requests
       ▼
┌─────────────────────┐
│  FastAPI (port 8082)│  ← Python API wrapper
└──────┬──────────────┘
       │
       ├────────────────────┐
       │                    │
       ▼                    ▼
┌─────────────┐      ┌──────────────┐
│  ChromaDB   │      │   Ollama     │
│  (port 8000)│      │  (port 11434)│
│             │      │              │
│ Vector DB   │      │ LLM Engine   │
│ for company │      │ Runs models  │
│ documents   │      │              │
└─────────────┘      └──────────────┘
```

## File Structure

```
/docker/goldco-ai/
├── docker-compose.yml          # Defines all 3 containers
├── api/
│   ├── Dockerfile             # Builds the Python API container
│   ├── requirements.txt       # Python dependencies
│   └── api.py                 # Main API code
└── company_docs/              # Put your data files here (currently empty)
```

## The Two Models (Why We Have Both)

### Mistral 7B (mistral:7b-instruct-q4_K_M)
- **Size:** 4.1GB
- **Speed:** 30-60 seconds per response
- **Use case:** Deep analysis, trend spotting, strategic insights
- **Quality:** Smart, analytical, nuanced
- **Default model** when you don't specify

### Llama 3.2 3B (llama3.2:3b-instruct-q4_K_M)
- **Size:** 2.1GB
- **Speed:** 10-15 seconds per response
- **Use case:** Quick lookups, simple questions, "read me the data"
- **Quality:** Fast but less analytical depth

**Why both?** You said you need both quick data retrieval AND deep analysis. The fast model handles "what did we do in Q3?" while the smart model handles "analyze Q3 trends and recommend actions."

## Current Configuration

**Docker Compose Services:**
1. **ollama** - AI model engine (port 11434)
2. **chromadb** - Vector database v0.5.23 (port 8000)
3. **goldco-api** - FastAPI wrapper (port 8082)

**Models Downloaded:**
- mistral:7b-instruct-q4_K_M (4.1GB)
- llama3.2:3b-instruct-q4_K_M (2.1GB)

**Data Loaded:**
Currently just 3 test sentences. Real data ingestion pending.

## How To Use The System

### Check System Health
```bash
curl http://localhost:8082/health
```
Returns JSON showing if ChromaDB and Ollama are connected, plus available models.

### Ask Questions (Fast Model)
```bash
curl -X POST http://localhost:8082/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What was our Q3 Gold IRA performance?", "model": "llama3.2:3b-instruct-q4_K_M"}'
```

### Ask Questions (Smart Model - Default)
```bash
curl -X POST http://localhost:8082/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Analyze our Q3 campaigns and suggest improvements"}'
```

### Load Test Data
```bash
curl -X POST http://localhost:8082/ingest
```

## Important Commands

### View Container Logs
```bash
docker logs goldco-api
docker logs ollama
docker logs chromadb
```

### Restart Everything
```bash
cd /docker/goldco-ai
docker compose restart
```

### Stop Everything
```bash
docker compose down
```

### Start Everything
```bash
docker compose up -d
```

### Rebuild API After Code Changes
```bash
docker compose up -d --build
```

### Download New Models
```bash
docker exec ollama ollama pull <model-name>
```

### Run Commands Inside Containers
```bash
docker exec -it goldco-api bash    # Access API container
docker exec -it ollama bash        # Access Ollama container
docker exec -it chromadb bash      # Access ChromaDB container
```

## What's Working

✅ Ollama running both models
✅ ChromaDB storing and retrieving data
✅ FastAPI connecting everything
✅ RAG pipeline working (search docs → feed to AI → get answer)
✅ Model selection (can choose fast vs smart)
✅ Test queries returning valid responses

## What's NOT Done Yet

❌ Real company data ingestion (only test data loaded)
❌ Chat interface (currently just curl commands)
❌ Custom data ingestion scripts for your CSVs/reports
❌ Web UI for easier interaction

## Performance Notes

**Response Times:**
- Fast model (Llama 3B): 10-15 seconds
- Smart model (Mistral 7B): 30-60 seconds

**Resource Usage:**
- Idle: ~1-2GB RAM
- With model loaded: ~6GB RAM
- CPU spikes to 100% during inference (shows as ~10% on system monitoring due to 2-core averaging)

**Bottleneck:** CPU cores (only have 2). RAM is fine. More cores = faster responses, but 2 cores is workable for your use case.

## Next Steps

1. **Build chat interface** - Web UI or CLI tool for easier interaction
2. **Load real data** - Ingest your actual Goldco marketing/sales data
3. **Custom ingestion scripts** - Based on your data format (CSVs, PDFs, etc.)
4. **Automation** - Background jobs for data analysis

## Accessing From Outside The Server

Currently the API only listens on localhost (127.0.0.1). To access from your local machine, you'd need to:

1. Set up reverse proxy (nginx)
2. Add SSL certificate
3. Configure firewall rules

OR

Just SSH tunnel:
```bash
ssh -L 8082:localhost:8082 root@your-vps-ip
```
Then access at http://localhost:8082 on your local machine.

## Troubleshooting

**"Port already allocated" error:**
Change port in docker-compose.yml from 8080 to something else (we use 8082).

**"Could not connect to tenant" error:**
ChromaDB version mismatch. Make sure both server and client are v0.5.23.

**API returns empty response:**
Check logs with `docker logs goldco-api` - likely a Python error not being displayed.

**Model takes forever:**
Normal. 2 CPU cores = slow inference. Use fast model for quick queries.

**RAM maxed out:**
You're running a 7B model on 8GB RAM. This is expected. Don't run other heavy processes simultaneously.

## Version Info

- **ChromaDB:** 0.5.23 (both server and Python client)
- **Ollama:** Latest (downloaded Nov 2025)
- **Python:** 3.11
- **FastAPI:** 0.104.1

## Contact Points

**API Endpoints:**
- `http://localhost:8082/` - Status check
- `http://localhost:8082/health` - System health
- `http://localhost:8082/ask` - Ask questions (POST)
- `http://localhost:8082/ingest` - Load data (POST)

**Container Names:**
- `goldco-api`
- `ollama`
- `chromadb`

---

**Date Setup Completed:** November 3, 2025
**Status:** System operational, awaiting real data and chat interface
