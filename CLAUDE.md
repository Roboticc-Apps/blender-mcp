# Project Instructions for Claude Code

## 🚨 CRITICAL RULES - ALWAYS FOLLOW THESE

1. **ALWAYS use web search for current information**
   - When asked about libraries, packages, or APIs, ALWAYS search for latest versions
   - Never rely on potentially outdated training data for technical questions
   - Use `use context7` for up-to-date documentation

2. **ALWAYS use the virtual environment**
   - This project uses venv (or specify: poetry/conda/etc)
   - Before ANY pip command: `source .venv/bin/activate`
   - Never install packages globally

3. **ALWAYS use Context7 for documentation**
   - When writing code with external libraries, use: `use context7`
   - This ensures version-specific, up-to-date code examples

4. **STAY IN PROJECT DIRECTORY**
   - You can only work in THIS folder and its subfolders
   - Never access parent directories
   - Never modify files outside this project

5. **NEVER commit without explicit permission**
   - Only commit when user explicitly says "commit" or "push"
   - Always run tests before committing

---

## 📦 Environment Setup

- **Virtual Environment**: `.venv/`
- **Activation**: `source .venv/bin/activate`
- **Dependencies**: `pip install -r requirements.txt` (or `npm install`)

---

## 🔧 Project Commands

### Testing
- `pytest` or `npm test`
- Always run tests after code changes

### Linting & Formatting
- `ruff check` or `npm run lint`
- `black .` or `prettier --write .`

### Build
- `npm run build` or `python setup.py build`

### Run
- `python main.py` or `npm start`

---

## 💻 Code Style

- Use latest TypeScript/Python best practices (search for current standards)
- Add type hints to all Python functions
- Use ES modules (`import/export`), not CommonJS
- Destructure imports when possible
- Follow PEP 8 for Python, ESLint rules for JavaScript

---

## 🔄 Workflow

1. **Before coding**: Activate virtual environment
2. **During coding**: 
   - Use web search to verify latest best practices
   - Use Context7 for library-specific code
   - Ask clarifying questions for complex tasks
3. **After coding**:
   - Run tests
   - Run linter
   - Only commit when explicitly told

---

## 📂 File Structure

- `.venv/` - Virtual environment (DO NOT MODIFY)
- `.env` - Environment variables (DO NOT READ OR MODIFY)

---

## ⚠️ What NOT to Do

- ❌ Do NOT commit without being asked
- ❌ Do NOT install packages globally
- ❌ Do NOT access files outside this project
- ❌ Do NOT modify .env or secrets
- ❌ Do NOT use outdated examples - always search for current info
- ❌ Do NOT skip using Context7 when working with libraries