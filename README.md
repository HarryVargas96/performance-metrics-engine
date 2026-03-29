# Performance Metrics Engine 🏃‍♂️🚴‍♀️

An AI-powered training data pipeline and dashboard designed to ingest raw workout data from the Strava API, compute advanced **Performance Management Chart (PMC)** metrics like Chronic Training Load (CTL), Acute Training Load (ATL), Training Stress Score (TSS), and Fatigue. It ultimately acts as a context engine for Google's Gemini LLM—fed with sports science literature—to generate highly personalized, science-based coaching insights.

## Project Vision 🚀
The fundamental goal of this project is to build a Virtual Endurance Coach. By marrying sports science with cutting-edge artificial intelligence, this engine will:
1. **Automate Data Extraction:** Continuously pull workout data (distance, duration, heart rate, power, perceived exertion) directly from your devices via Strava.
2. **Compute Real Physiological Metrics:** Replicate complex calculations typically reserved for premium platforms like TrainingPeaks (calculating rolling averages for CTL, ATL, and TSS).
3. **Generate Actionable Insights using Generative AI:** Feed these daily metrics, along with curated sports science literature (via **Google NotebookLM** documents), into **Gemini** to answer questions like:
   - *"Am I overtraining based on my current TSS ramp rate?"*
   - *"What kind of workout should I do tomorrow to achieve a positive Form (TSB) for my race this weekend?"*

## Technology Stack 🛠️

### Data Engineering & Processing
*   **Python**: The core language for the backend engine.
*   **Poetry**: Robust dependency management and deterministic virtual environments.
*   **Strava API (v3)**: The primary data source (OAuth2 dynamic fetching).
*   **Jupyter Notebooks**: Iterative environment for API exploration and data cleaning.
*   **Pandas / Polars**: For intensive feature engineering and time-series calculations (PMC metrics).

### AI & LLM Integration
*   **Google Gemini**: The reasoning engine that will analyze processed metrics and deliver conversational coaching.
*   **NotebookLM context**: Used as a grounding knowledge source containing academic papers on periodization and endurance training load management, providing hyper-specialized context to Gemini's prompts.

### Future Visualization (Dashboard)
*   **Streamlit / Next.js (TBD)**: An interactive frontend where the athlete can view daily PMC charts and chat directly with their AI coach in real-time.

## Development Roadmap
*   ✅ **Phase 1 [Current]:** Repository scaffolding, robust OAuth2 setup, and basic `StravaClient` API extraction.
*   🔜 **Phase 2:** Exploratory Data Analysis (EDA) in Jupyter, extracting metrics like Moving Time and Heart Rate to calculate historical TSS, ATL, and CTL.
*   🔜 **Phase 3:** Orchestrating the Gemini LLM pipeline and structured prompt engineering with NotebookLM context.
*   🔜 **Phase 4:** Frontend Dashboard development and deployment.

---
*Developed for training optimization and data-driven athletic performance.*
