# Car Dealer Assistant

A chat assistant that helps someone find a car and the dealer who sells it. The catalog is CSV data in `inputs/`. The assistant uses an OpenAI-compatible chat model to understand the shopper and write replies, and it only states cars, prices, and dealer contact details that the catalog search returns.

The app is a FastAPI backend plus a React chat UI. Each conversation is stored in PostgreSQL: user messages, assistant messages, and short embedded memories of earlier turns.

## Setup

Requirements: Python 3.12+, PostgreSQL with the [pgvector](https://github.com/pgvector/pgvector) extension, and Node.js for the web UI. [uv](https://docs.astral.sh/uv/) is the easiest way to install the Python package.

```bash
cp .env.example .env
```

Set these in `.env`:

| Variable               | Purpose                                                                                                                      |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `DATABASE_URL`         | Postgres URL, for example `postgresql://user:pass@localhost:5432/car_dealer`. `postgresql://` is rewritten to use `asyncpg`. |
| `JWT_SECRET_KEY`       | Secret used to sign login tokens.                                                                                            |
| `MODEL_API_KEY`        | API key for the chat and embedding models. Never commit this.                                                                |
| `MODEL_BASE_URL`       | OpenAI-compatible base URL. The default targets Gemini.                                                                      |
| `MODEL_CHAT_NAME`      | Chat model. Default `gemini-2.5-flash`.                                                                                      |
| `MODEL_EMBEDDING_NAME` | Embedding model used for conversation memory. Default `gemini-embedding-2`.                                                  |

`CARS_CSV` and `DEALERS_CSV` are optional. They default to `inputs/cars.csv` and `inputs/dealers.csv`.

```bash
uv sync --group dev
```

Create the database and enable pgvector (`CREATE EXTENSION IF NOT EXISTS vector;`).

This checkout does not include an Alembic revision yet. From the repo root, with `.env` pointing at that database:

```bash
uv run alembic upgrade head
```

If the database already has tables from an older checkout, do not autogenerate over them. Message rows stay as they are: `user`, `assistant`, and `memory`, including embeddings.

## Run the chatbot

Backend, from the repo root:

```bash
uv run uvicorn app.main:app --reload
```

Or `bash scripts/run_server.sh`. Health check: `GET http://127.0.0.1:8000/health`.

Frontend, from `frontend/`:

```bash
cp example.env .env
npm install
npm run dev
```

Open `http://localhost:5173`, register or sign in, and chat. `VITE_API_BASE_URL` must include the `/api` prefix (see `frontend/example.env`). Backend `CORS_ORIGINS` must include the Vite origin.

A new chat starts with “Hi! Which car are you looking to buy?”. Name a car, pick a listing if several dealers stock it, then ask for the dealer’s details or a call. A call asks for a date and time and prints a confirmation. Nothing is booked in a calendar.

History stays in the database. Open **History** to resume a conversation. **New chat** starts another one.

## Tests

```bash
uv run pytest
```

The tests cover catalog loading, car lookup, dealer matching, and the dialogue steps (not found, several matches, dealer details, and call confirmation). They do not call the model or the database.

## Data design

Two CSV files:

- `inputs/dealers.csv`: `id`, `name`, `phone`, `email`, `city`, `address`. One row per dealership.
- `inputs/cars.csv`: `id`, `make`, `model`, `variant`, `price`, `dealer_id`. `dealer_id` points at `dealers.id`.

The same make, model, and variant can appear more than once when different dealers stock it. Price is an integer in Pakistani rupees, matching the cities in the dealer file. The assistant shows it as `PKR 9,250,000`.

Lookup is exact against those files. The model does not choose which rows exist. It extracts the car phrase, whether the shopper wants dealer details or a call, and any date and time. Python then searches the CSV and tells the model which stage to answer and which facts it may quote.

## How a message is handled

1. The latest user and assistant messages are loaded from the database, oldest first.
2. The model reads that chat and returns JSON: car phrase, option (`details` or `call`), and slot.
3. The catalog is searched. Make and model select the rows. Variant words, dealer name, and city narrow them. At most eight listings are passed through.
4. A stage is chosen: ask for a car, ask for a model, list matches, offer details or a call, print dealer details, ask for a time, or confirm the call.
5. The model writes the reply from that stage and the catalog text. Phone, email, and address are included in the prompt only when the stage is dealer details or a call confirmation.
6. The user message and the assistant reply are saved. A background task may store a short embedded summary when the exchange names a car, a dealer, or a time, so a later message in the same chat can recall it.

## Edge cases

| Situation                                              | What happens                                                                                                                      |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| The car is not in the CSV                              | The shopper is told it was not found and asked for another make or model. No similar car is invented.                             |
| Only a make is given (“Toyota”)                        | The assistant lists models in stock for that make and asks which one.                                                             |
| Several variants or dealers match                      | They are listed (up to eight) and the shopper is asked to pick one. A call is not confirmed until one listing is in focus.        |
| Dealer details or a call before a single car is chosen | The assistant asks them to pick a listing first.                                                                                  |
| A call with no date or time                            | The assistant asks for a preferred date and time. The slot is kept in the shopper’s words.                                        |
| Dealer id on a car has no dealer row                   | The car can still be found. Contact details are not invented; the reply says the dealer record is missing.                        |
| Empty or whitespace message                            | The API rejects it.                                                                                                               |
| CSV missing, empty, or missing columns                 | Startup logs the error. A chat request returns 503 until the files are fixed. Duplicate ids keep the first row and log a warning. |
| The model returns invalid JSON                         | The shopper’s own message is searched as the car phrase.                                                                          |
| The model API fails                                    | Both turns are still saved. The assistant reply is an apology asking them to try again. Memory is skipped for that turn.          |
| Off-topic chat                                         | The prompt sends the conversation back to finding a car.                                                                          |
| Another user’s conversation id                         | The API returns 404.                                                                                                              |

## Assumptions

- One assistant serves the whole catalog. Dealers are rows in the CSV, not separate chatbots.
- “Schedule a call” only prints a confirmation with the dealer name, phone, and the slot the shopper gave. No SMS, calendar, or dealer system is contacted.
- The shopper must be signed in. That is how history is stored per person.
- Prices are shown even though the sample dialogue does not include them, because the CSV has them and they help compare listings.
- Common words that are also model names (Honda City) depend on the model extracting a real car phrase. A bare “which city” should not be treated as that model.
- Conversation memory is a summary embedding, not a second copy of the catalog. The catalog remains the source of truth when they disagree.
