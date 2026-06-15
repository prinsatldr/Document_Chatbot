from flask import Flask, render_template, request, session, redirect
from pypdf import PdfReader
from flask import send_from_directory
import pymysql
import os
from ollama import chat
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from flask import flash, redirect,url_for
from flask import jsonify
from flask_cors import CORS
import whisper
from dotenv import load_dotenv
import os

load_dotenv()

whisper_model = whisper.load_model("base")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
CORS(app)

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

index = faiss.IndexFlatL2(384)

chunk_store = []

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def get_db_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT"))
    )


def extract_pdf_text(pdf_path):

    reader = PdfReader(pdf_path)

    text = ""

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text


def chunk_text(text):

    words = text.split()

    chunk_size = 300
    overlap = 50

    chunks = []

    for i in range(0, len(words), chunk_size - overlap):

        chunk = " ".join(
            words[i:i + chunk_size]
        )

        chunks.append(chunk)

    return chunks

def save_document(filename, text):

    conn = get_db_connection()

    cursor = conn.cursor()

    query = """
    INSERT INTO documents
    (filename, content)
    VALUES (%s, %s)
    """

    cursor.execute(query, (filename, text))

    conn.commit()
    conn.close()


def save_chunks(filename, chunks):

    conn = get_db_connection()

    cursor = conn.cursor()

    for chunk in chunks:

        cursor.execute(
            """
            INSERT INTO document_chunks
            (filename, chunk_text)
            VALUES (%s, %s)
            """,
            (filename, chunk)
        )

    conn.commit()
    conn.close()

def search_chunks(question, top_k=3):

    question_embedding = model.encode(
        [question]
    )

    distances, indices = index.search(
        np.array(question_embedding).astype("float32"),
        top_k
    )

    results = []

    for idx in indices[0]:

        if idx < len(chunk_store):

            results.append(
                chunk_store[idx]
            )
    print("Question:", question)
    print("Distance:", distances[0][0])
    print("Index:", indices[0][0])
    print("Chunk:")
    print(results[0][:300])
    print("-" * 50)
    return (
    "\n\n".join(results),
    distances[0][0]
)


def get_ai_answer(question, document_text, chat_history):

    document_text = document_text[:1500]

    conversation = ""

    for msg in chat_history:
        conversation += f"{msg['role']}: {msg['content']}\n"

    prompt = f"""
Answer the question using the information below.

Be concise.
Be direct.
Do not mention documents, context, sources, or uploaded files.

Conversation:
{conversation}

Information:
{document_text}

Question:
{question}
"""

    response = chat(
        model="llama3.2",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]

@app.route("/")
def root():

    return redirect(
        "/chat"
    )

@app.route("/login")
def login_page():

    return render_template(
        "login.html"
    )

@app.route(
    "/login",
    methods=["POST"]
)
def login():

    username = request.form["username"]

    password = request.form["password"]

    if (
        username == ADMIN_USERNAME
        and
        password == ADMIN_PASSWORD
    ):

        session["admin"] = True

        return redirect("/admin")

    flash(
        "Invalid username or password!"
    )

    return redirect("/login")

@app.route("/admin")
def home():

    if not session.get(
        "admin"
    ):

        return redirect(
            "/login"
        )

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, filename
        FROM documents
        ORDER BY id DESC
    """)

    documents = cursor.fetchall()

    conn.close()

    return render_template(
        "upload.html",
        documents=documents
    )

@app.route("/logout")
def logout():

    session.pop(
        "admin",
        None
    )

    return redirect(
        "/login"
    )

@app.route("/upload", methods=["POST"])
def upload():

    file = request.files["document"]

    if file.filename == "":
        return "No file selected"

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        file.filename
    )

    file.save(filepath)

    text = extract_pdf_text(filepath)

    print("\n----- PDF CONTENT -----")
    print(text[:500])
    print("-----------------------\n")

    # Save complete document
    save_document(file.filename, text)

    # Save chunks for future vector search
    chunks = chunk_text(text)

    save_chunks(
        file.filename,
        chunks
    )

    embeddings = model.encode(
        chunks
    )

    index.add(
        np.array(embeddings).astype("float32")
    )

    chunk_store.extend(
        chunks
    )

    flash("PDF uploaded successfully!")
    return redirect("/admin")


@app.route("/chat")
def chatbot():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, filename
        FROM documents
        ORDER BY id DESC
    """)

    documents = cursor.fetchall()

    conn.close()

    return render_template(
        "chat.html",
        chat_history=session.get(
            "chat_history",
            []
        ),
        documents=documents
    )


@app.route(
    "/search",
    methods=["POST"]
)
def search():

    question = request.form["question"]

    if "chat_history" not in session:

        session["chat_history"] = []

    chat_history = session["chat_history"]

    if index.ntotal == 0:

        answer = "No document uploaded."

    else:

        followups = [
            "explain more",
            "tell me more",
            "more",
            "why",
            "how",
            "example",
            "give example",
            "advantages",
            "benefits",
            "disadvantages"
        ]

        if question.lower() in followups:

            search_query = (
                session.get(
                    "last_topic",
                    ""
                )
                + " "
                + question
            )

        else:

            session["last_topic"] = question

            search_query = question

        document_text, score = search_chunks(
            search_query
        )

        if score > 3:

            answer = (
                "Sorry, I couldn't find relevant information."
            )

        else:

            answer = get_ai_answer(
                question,
                document_text,
                chat_history
            )

    chat_history.append(
        {
            "role": "user",
            "content": question
        }
    )

    chat_history.append(
        {
            "role": "assistant",
            "content": answer
        }
    )

    session["chat_history"] = chat_history[-10:]

    return jsonify(
        {
            "answer": answer
        }
    )


@app.route("/delete/<int:doc_id>")
def delete_document(doc_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT filename
        FROM documents
        WHERE id=%s
    """, (doc_id,))

    result = cursor.fetchone()

    if result:

        filename = result[0]

        cursor.execute("""
            DELETE FROM document_chunks
            WHERE filename=%s
        """, (filename,))

        cursor.execute("""
            DELETE FROM documents
            WHERE id=%s
        """, (doc_id,))

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        if os.path.exists(filepath):
            os.remove(filepath)

        conn.commit()

    conn.close()

    return redirect("/admin")

@app.route(
    "/clear_chat",
    methods=["POST"]
)
def clear_chat():

    session.pop(
        "chat_history",
        None
    )

    session.pop(
        "last_topic",
        None
    )

    return redirect(
        "/chat"
    )

@app.route(
    "/auto_logout",
    methods=["POST"]
)
def auto_logout():

    session.pop(
        "admin",
        None
    )

    return "", 204

from flask import jsonify

@app.route(
    "/api/chat",
    methods=["POST"]
)
def api_chat():

    question = request.form["question"]

    if index.ntotal == 0:

        answer = "No document uploaded."

    else:

        document_text, score = search_chunks(
            question
        )

        if score > 3:

            answer = (
                "Sorry, I couldn't find relevant information."
            )

        else:

            answer = get_ai_answer(
                question,
                document_text,
                []
            )

    return jsonify(
        {
            "answer": answer
        }
    )

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )

def load_existing_chunks():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT chunk_text
        FROM document_chunks
    """)

    results = cursor.fetchall()

    conn.close()

    if len(results) == 0:
        return

    all_chunks = [
        row[0]
        for row in results
    ]

    embeddings = model.encode(
        all_chunks
    )

    index.add(
        np.array(embeddings).astype("float32")
    )

    chunk_store.extend(
        all_chunks
    )

    print(
        f"Loaded {len(all_chunks)} chunks into FAISS."
    )

@app.route("/voice", methods=["POST"])
def voice():
        audio = request.files["audio"]

        audio.save("recording.webm")

        result = whisper_model.transcribe(
            "recording.webm"
        )

        question = result["text"]

        document_text, score = search_chunks(
            question
        )

        if score > 3:

            answer = (
                "Sorry, I couldn't find relevant information."
            )

        else:

            answer = get_ai_answer(
                question,
                document_text,
                []
            )

        return jsonify({
            "transcript": question,
            "answer": answer
    })

if __name__ == "__main__":

    load_existing_chunks()

    app.run(debug=True)