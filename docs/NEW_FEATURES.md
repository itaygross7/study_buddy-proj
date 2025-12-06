# New Features Guide - StudyBuddyAI

This document describes the new features added to StudyBuddyAI, including the Triple Hybrid AI system and interactive learning tools.

## 🚀 Triple Hybrid AI System

StudyBuddyAI now uses an intelligent AI routing system that automatically selects the best model for each task, optimizing both cost and performance.

### How It Works

The system intelligently routes requests to different AI models based on the task:

- **Heavy Files** (Audio/Long PDFs): → Gemini 1.5 Flash (native multimodal support)
- **Quiz Generation**: → GPT-4o-mini with JSON enforcement
- **Standard Tasks**: → GPT-4o-mini (chat, summaries)
- **Complex Reasoning**: → GPT-4o (advanced math, complex logic)
- **Baby Capy Mode**: → GPT-4o-mini with simplified prompts

### Benefits

1. **Cost Optimization**: Uses cheaper models for simple tasks, expensive ones only when needed
2. **Better Performance**: Native multimodal processing for files, JSON mode for structured output
3. **Reliability**: Automatic retries with exponential backoff
4. **Backward Compatible**: Existing code continues to work without changes

### Configuration

Set these environment variables in your `.env` file:

```bash
# AI API Keys (required)
OPENAI_API_KEY="your_openai_api_key"
GEMINI_API_KEY="your_gemini_api_key"

# Model Selection (optional - defaults shown)
SB_OPENAI_MODEL="gpt-4o-mini"        # For standard tasks
SB_GEMINI_MODEL="gemini-1.5-flash-latest"   # For heavy files
SB_DEFAULT_PROVIDER="gemini"         # Default provider
```

---

## 🍼 Baby Capy Mode

A fun, educational feature that simplifies AI explanations using cute capybara-themed language.

### What It Does

When Baby Capy mode is active:
- Avner's avatar changes to a baby capybara (`baby_avner.png`)
- Explanations use simple words and short sentences
- Analogies involve water, napping, and tangerines (capybara favorites!)
- Complex topics broken into tiny, digestible pieces

### How to Use

**Via API:**
```javascript
fetch('/api/avner/ask', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        question: "Explain photosynthesis",
        baby_mode: true
    })
});
```

**Via JavaScript:**
```javascript
// Assuming you have an AvnerAvatar instance
avner.setBabyMode(true);  // Enable Baby Capy mode
avner.setBabyMode(false); // Disable Baby Capy mode
```

### Use Cases
- Introducing complex topics to beginners
- Breaking down difficult concepts
- Making learning more fun and accessible
- Reducing anxiety around challenging material

---

## 📚 Course Wiki / Auto-Glossary

Automatically extracts and organizes key terms from your course materials.

### Features

- **Auto-Extraction**: Terms automatically extracted when you generate summaries
- **Searchable**: Full-text search across terms and definitions
- **Organized by Course**: Each course has its own glossary
- **Source Tracking**: Know which document each term came from

### How to Access

1. Navigate to a course in your library
2. Click on "Wiki" or visit `/glossary/<course_id>`
3. Use the search bar to find specific terms
4. Browse all terms in alphabetical order

### API Endpoints

```bash
# Get all terms for a course
GET /api/glossary/course/<course_id>

# Search terms
POST /api/glossary/search
{
    "query": "photosynthesis",
    "course_id": "course_123"
}
```

---

## 🎓 Interactive Tutor Mode

Step-by-step guided learning with AI-powered teaching and assessment.

### How It Works

1. **Create Session**: Choose a topic you want to learn
2. **AI Generates Syllabus**: 5-step learning path created automatically
3. **Step-by-Step Teaching**: 
   - Explanation of the concept
   - Real-world example
   - Drill question to test understanding
4. **Answer Evaluation**: AI checks your answer and provides feedback
5. **Progress Tracking**: Move forward when ready, repeat if needed

### Features

- **Adaptive Learning**: Moves at your pace
- **Instant Feedback**: Know immediately if your answer is correct
- **Complete Syllabus**: See your learning path upfront
- **Progress Tracking**: Visual checklist of completed steps
- **Course Integration**: Optional course context for personalized teaching

### How to Use

1. Go to `/tool/tutor`
2. Enter a topic (e.g., "Machine Learning Basics")
3. AI creates a 5-step syllabus
4. Work through each step
5. Answer drill questions to progress

### API Endpoints

```bash
# Create new session
POST /api/tutor/create
{
    "topic": "Calculus derivatives",
    "course_id": "optional_course_123"
}

# Get teaching content for current step
POST /api/tutor/<session_id>/teach

# Submit answer
POST /api/tutor/<session_id>/answer
{
    "answer": "Your answer here"
}

# List all sessions
GET /api/tutor/sessions
```

---

## 📊 Visual Diagram Generator

Create educational diagrams automatically using Mermaid.js.

### Supported Diagram Types

1. **Flowchart**: Process flows, algorithms
2. **Mind Map**: Concept relationships, brainstorming
3. **Timeline**: Historical events, project phases
4. **Sequence**: Interactions, protocols
5. **Class Diagram**: Object-oriented design
6. **State Diagram**: State machines, workflows

### Features

- **AI-Powered**: Describe what you want, AI creates the diagram
- **Instant Preview**: See diagram rendered immediately
- **Mermaid.js Code**: Copy the code for use in other tools
- **Beautiful Theming**: Matches StudyBuddy's cozy aesthetic

### How to Use

1. Go to `/tool/diagram`
2. Enter what you want to visualize (e.g., "Water cycle")
3. Choose diagram type
4. Click "Generate Diagram"
5. View, copy, or save the result

### API Endpoint

```bash
POST /api/diagram/generate
{
    "topic": "Software development process",
    "type": "flowchart"
}
```

### Mermaid.js Integration

Diagrams automatically render in the browser. The Mermaid.js library is loaded in `base.html`:

```html
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
```

---

## 🔧 Technical Details

### Database Models

**New Collections:**

```python
# Glossary Terms
class CourseTerm:
    term: str
    definition: str
    source_file: str
    course_id: str
    user_id: str

# Tutor Sessions
class TutorSession:
    user_id: str
    topic: str
    syllabus: List[str]
    current_step: int
    chat_history: List[Dict]
    completed_steps: List[int]
```

### Worker Integration

The background worker (`worker.py`) now includes:
- Automatic glossary extraction after summaries
- Non-blocking term extraction (failures don't affect summaries)
- Batch processing support

### Frontend Updates

**New Templates:**
- `glossary.html` - Course wiki/glossary page
- `tool_tutor.html` - Interactive tutor interface
- `tool_diagram.html` - Diagram generator

**Updated JavaScript:**
- `avner_animations.js` - Baby Capy mode support

**Updated Styles:**
- Mermaid.js theming matches StudyBuddy colors

---

## 🎯 Best Practices

### Using the Triple Hybrid System

1. **For Summaries**: Let the system choose automatically
2. **For Quizzes**: Explicitly use `task_type="quiz"` for JSON output
3. **For Large Files**: System automatically uses Gemini for efficiency
4. **For Math/Logic**: Use `task_type="complex_reasoning"` for GPT-4o

### Using Baby Capy Mode

1. **For Beginners**: Great for introducing new topics
2. **For Review**: Helps reinforce concepts in a fun way
3. **Not for Exams**: Regular mode is better for exam prep
4. **Toggle Easily**: Can switch mid-conversation

### Using the Glossary

1. **Review Before Exams**: Quick reference for key terms
2. **Build Over Time**: Automatically grows with your materials
3. **Search Effectively**: Use partial words to find related terms
4. **Share with Study Groups**: Export terms for collaboration

### Using Interactive Tutor

1. **Start Simple**: Choose topics you're somewhat familiar with
2. **Take Your Time**: No rush, repeat steps if needed
3. **Ask Follow-ups**: Use chat to clarify confusing points
4. **Track Progress**: Complete all steps for best retention

---

## 🐛 Troubleshooting

### AI Routing Issues

**Problem**: Wrong model being used
- Check environment variables are set correctly
- Verify API keys are valid
- Check logs for routing decisions

**Problem**: JSON parsing errors
- Ensure `require_json=True` for quiz tasks
- Check AI response in logs
- Try regenerating if first attempt fails

### Baby Capy Mode Issues

**Problem**: Avatar doesn't change
- Check `baby_avner.png` exists in `ui/Avner/`
- Verify JavaScript console for errors
- Ensure `setBabyMode()` is being called

### Glossary Issues

**Problem**: No terms extracted
- Ensure summaries are being generated
- Check worker logs for extraction errors
- Verify MongoDB connection

### Tutor Session Issues

**Problem**: Session doesn't progress
- Check if answer was submitted correctly
- Verify session ID matches
- Look for API errors in browser console

---

## 📝 Migration Guide

### For Existing Code

The Triple Hybrid system is **backward compatible**. Existing code like:

```python
from src.services.ai_client import ai_client
result = ai_client.generate_text(prompt, context)
```

Will continue to work without changes. To use new features:

```python
# Use JSON mode for quizzes
result = ai_client.generate_text(prompt, context, 
                                 task_type="quiz", 
                                 require_json=True)

# Use Baby Capy mode
result = ai_client.generate_text(prompt, context, 
                                 baby_mode=True)

# Use complex reasoning mode
result = ai_client.generate_text(prompt, context, 
                                 task_type="complex_reasoning")
```

### For Custom Integrations

If you've built custom integrations:

1. Update to use new task types for better performance
2. Enable JSON mode for structured output
3. Consider using Baby Capy mode for educational content
4. Integrate glossary and tutor APIs for enhanced features

---

## 🎉 What's Next?

Future enhancements planned:
- **Multilingual Glossary**: Terms in multiple languages
- **Tutor Voice Mode**: Audio explanations
- **Diagram Collaboration**: Share and edit diagrams
- **Advanced Analytics**: Track learning progress over time
- **Custom AI Routing**: User-defined routing rules

---

For questions or issues, please open an issue on GitHub or contact support.
