# GambleApp

GambleApp is a browser-based multiplayer gambling platform where players wager on skill-based 2D games. The stack includes a SvelteKit frontend, FastAPI backend, and Colyseus for real-time multiplayer networking.

## Getting Started

This project consists of three main components: backend, Colyseus server, and frontend.

### Backend (FastAPI)

Runs the main API server using FastAPI.

**Start the backend:**

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Make sure all required Python dependencies are installed. You can install them using:

```bash
pip install -r requirements.txt
```

### Multiplayer Server (Colyseus)

Handles real-time game sessions and player communication.

**Start the Colyseus server:**

```bash
node index.js
```

Ensure Node.js dependencies are installed first:

```bash
npm install
```

### Frontend (SvelteKit)

Provides the client interface and game rendering.

**Start the frontend:**

```bash
npm run start
```

Install dependencies if needed:

```bash
npm install
```

## Folder Structure

- `backend/` — FastAPI server and business logic  
- `colyseus-server/` — Node.js Colyseus rooms and matchmaking  
- `frontend/` — SvelteKit app for user interface and gameplay  

## Notes

- The frontend connects to the Colyseus server at `ws://localhost:2567`.  
- Ensure all three services are running simultaneously for full functionality.

## License

This project is private property