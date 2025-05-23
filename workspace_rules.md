# 🔁 Project Awareness
- Always read `PLANNING.md` and `TASK.md` at the start of a conversation.
- Update `TASK.md` with completed tasks and new subtasks after changes.
- All work must follow the architectural and stylistic constraints of `PLANNING.md`.

# 🧱 Code Structure
- Never create files longer than 500 lines.
- Use clean modular code, PEP8 style, and type hints.
- Write docstrings for every function (Google style).

# 🧪 Testing
- All new functions must include tests:
  - 1 successful case
  - 1 failure case
  - 1 edge case
- Use `pytest` for Python and React Testing Library for frontend.

# 🧠 AI Feedback Behavior
- When asked to generate AI feedback functions, include:
  - grammar correction
  - fluency score
  - rewrite suggestions
  - tone/emotion tagging
  - side-by-side translation
- Do not hallucinate libraries or undefined tools.

# 📎 Style & Docs
- Use `pydantic` for validation if needed.
- Maintain `README.md` actively.
- Comment complex logic.
- Keep prompts/feedback explainable and educational for users. 