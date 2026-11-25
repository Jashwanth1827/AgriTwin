"""Build the AgriTwin mini project report in DOCX and PDF.

Usage:  python scripts/build_mini_report.py
Outputs:
  docs/AgriTwin_Mini_Project_Report.docx
  docs/AgriTwin_Mini_Project_Report.pdf
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from report_design import (  # noqa: E402
    bullets,
    build_docx,
    build_pdf,
    centered,
    code,
    figure,
    h1,
    h2,
    h3,
    make_diagrams,
    numbered,
    p,
    page_break,
    spacer,
    table,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs"
DIAGRAM_DIR = Path(tempfile.gettempdir()) / "agritwin_report_diagrams"

TITLE = "AGRITWIN: REAL-DATA DIGITAL TWIN FOR CROP HEALTH, YIELD, MARKET AND DECISION SUPPORT"

COVER = [
    centered("A MINI PROJECT REPORT", "subtitle"),
    spacer(18),
    centered("On", "p"),
    spacer(18),
    centered(TITLE, "title"),
    spacer(34),
    centered("Submitted to", "p"),
    centered("OSMANIA UNIVERSITY", "bold"),
    spacer(12),
    centered("In partial fulfillment of the requirements for the award of", "p"),
    centered("BACHELOR OF ENGINEERING", "bold"),
    centered("in", "p"),
    centered("COMPUTER SCIENCE AND ENGINEERING (AI & ML)", "bold"),
    spacer(26),
    centered("by", "p"),
    centered("Aravapalli Jashwanth 245523748071", "p"),
    centered("Kolluru Sai Vamshi 245523748097", "p"),
    centered("Mandula Sri Sreshta 245523748103", "p"),
    spacer(28),
    centered("Under the esteemed guidance of", "p"),
    centered("Mrs. D . Padmaja Usha Rani", "bold"),
    centered("Assistant Professor", "p"),
    spacer(30),
    centered("DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING", "bold"),
    centered("KESHAV MEMORIAL ENGINEERING COLLEGE", "p"),
    centered("(Approved by AICTE, New Delhi & Affiliated to Osmania University, Hyderabad)", "p"),
    centered("D.No. 10 TC-111, Kachavanisingaram (V), Ghatkesar (M), Medchal-Malkajgiri, Telangana – 500088", "p"),
    spacer(22),
    centered("July 2026", "p"),
]

FRONT = [
    page_break(),
    centered("KESHAV MEMORIAL ENGINEERING COLLEGE", "bold"),
    centered("Department of Computer Science and Engineering (AI & ML)", "p"),
    centered("CERTIFICATE", "bold"),
    spacer(10),
    p(
        'This is to certify that the project report entitled "AgriTwin: Real-Data Digital Twin for '
        'Crop Health, Yield, Market and Decision Support" that is being submitted by Aravapalli '
        'Jashwanth(245523748071), Kolluru Sai Vamshi(245523748097), and Mandula Sri '
        'Sreshta(24553748103), under the guidance of Mrs. D. Padmaja Usha Rani for the fulfillment '
        'for the award of the degree of Bachelor of Engineering in Computer Science andEngineering(AI&ML)'
        'to theOsmaniaUniversity is a bonafide record of work carried out by them under my guidance and '
        'supervision. The results embodied in this project report have not been submitted to any other '
        'University or Institute for the award of any graduate degree.'
    ),
    spacer(30),
    table(
        "",
        ["Supervisor", "Project Coordinator"],
        [
            ["Mrs. D. Padmaja Usha Rani, Asst Prof\nDepartment of CSE(AI&ML)\nKeshav Memorial Engineering College,\nHyderabad.", "Dr. B. Devender, Asst Prof\nDepartment of CSE(AI&ML)\nKeshav Memorial Engineering College,\nHyderabad."],
        ],
        [1, 1],
    ),
    spacer(16),
    p("Dr. P. Bala Krishna, Assistant Professor"),
    spacer(18),
    p("Submitted for Viva-Voce Examination held on ______________________________"),
    spacer(18),
    table("", ["External Examiner", "Head of the Department"], [["", "Department of CSE(AI & ML)\nKeshav Memorial Engineering College"]], [1, 1]),

    page_break(),
    centered("ACKNOWLEDGEMENT", "bold"),
    spacer(8),
    p("This is to place on record our sincere appreciation and deep gratitude to all those whose support made this project successful."),
    p(
        "We are grateful to Mr. Neil Gogte, Founder Director, for providing all the necessary facilities and "
        "amenities required to carry out this project. It is with immense pleasure that we express our heartfelt "
        "gratitude to Prof. P. V. N. Prasad, Principal, Keshav Memorial Engineering College, for his continuous "
        "support and for giving us the opportunity to undertake this project."
    ),
    p(
        "We extend our sincere thanks to Ms. Deepa Ganu, Director Academics, for fostering an excellent academic "
        "environment in the college. We would like to express our special thanks to Dr. P. Naresh Kumar, Head of the "
        "Department, CSE(AI&ML), Keshav Memorial Engineering College, for their constant encouragement, inspiration, "
        "and for arranging all the facilities and resources required for the successful completion of our project."
    ),
    p(
        "We are deeply grateful to our internal Supervisor, Mrs. D. Padmaja Usha Rani, Assistant Professor, Department "
        "of CSE(AI&ML) Keshav Memorial Engineering College, for his/her valuable guidance, encouragement, and continuous "
        "moral support throughout the project, which greatly contributed to its success. We also extend our sincere thanks "
        "to our Project Coordinator, Dr. B. Devender, Assistant Professor, Department of CSE(AI&ML), Keshav Memorial "
        "Engineering College, for her guidance and support in the successful completion of our project."
    ),
    p(
        "Finally, we express our heartfelt gratitude to all the faculty members of the Department of CSE, as well as our "
        "friends and families, for their valuable suggestions, encouragement, and support in completing this project successfully."
    ),
    spacer(24),
    centered("Aravapalli Jashwanth 245523748071", "p"),
    centered("Kolluru Sai Vamshi 245523748097", "p"),
    centered("Mandula Sri Sreshta 245523748103", "p"),

    page_break(),
    centered("DECLARATION", "bold"),
    spacer(8),
    p(
        'This is to certify that the Major Project Titled " AGRITWIN: REAL-DATA DIGITAL TWIN FOR CROP HEALTH, YIELD, '
        'MARKET AND DECISION SUPPORT " that is submitted by Aravapalli Jashwanth (245523748071), Kolluru Sai Vamshi '
        '(245523748097), and Mandula Sri Sreshta(245523748103), under the guidance of Mrs. D. Padmaja Usha Rani for '
        'the fulfillment for the award of degree of Bachelor of Engineering in Computer Science andEngineering(AI&ML) '
        'to the Osmania University.'
    ),
    p(
        "We further declare that this project is a bonafide record of the work carried out by us under the guidance and "
        "supervision of Mrs. D. Padmaja Usha Rani. The results embodied in this project report have not been submitted to "
        "any other University or Institute for the award of any degree."
    ),
    spacer(24),
    centered("Name of the Student        Roll Number        Signature of the Student", "p"),

    page_break(),
    centered("VISION & MISSION OF KMEC", "bold"),
    h2("VISION OF THE INSTITUTE"),
    p("To be a leader in producing industry-ready and globally competent engineers to make India a world leader in software products and services."),
    h2("MISSION OF THE INSTITUTE"),
    numbered(
        [
            "To provide a conducive learning environment that inculcates problem solving skills, professional and ethical standards, lifelong learning through multimodal platforms and prepare students to become successful professionals.",
            "To forge industry-institute partnerships to expose students to the technology trends, work culture and ethics in the industry.",
            "To provide quality training to the students in the state-of-the-art software technologies and tools.",
            "To encourage research-based projects/activities in emerging areas of technology.",
            "To nurture entrepreneurial spirit among the students and faculty.",
            "To induce the spirit of patriotism among the students that enables them to understand India’s challenges and strive to develop effective solutions.",
        ]
    ),

    page_break(),
    centered("PROGRAM EDUCATIONAL OBJECTIVES (PEOS)", "bold"),
    p("PEO1: Graduates will have successful careers in computer related engineering fields or will be able to successfully pursue advanced higher education degrees."),
    p("PEO2: Graduates will try and provide solutions to challenging problems in their profession by applying computer engineering principles."),
    p("PEO3: Graduates will engage in life-long learning and professional development by rapidly adapting changing work environment."),
    p("PEO4: Graduates will communicate effectively, work collaboratively and exhibit high levels of professionalism and ethical responsibility."),

    page_break(),
    centered("VISION & MISSION OF DEPARTMENT", "bold"),
    h2("Vision of the CSE (AI & ML)"),
    p("To be a global center of excellence in Artificial Intelligence and Machine Learning, producing socially responsible graduates, excelling in education, research, and innovation for transformative societal impact."),
    h2("Mission of the CSE (AI & ML)"),
    numbered(
        [
            "To cultivate global expertise and ethical innovation in Artificial Intelligence & Machine Learning for lifelong impact.",
            "To provide top-tier education in Artificial intelligence, promoting industry collaboration and installing self-learning, team work and professional ethics.",
            "To establish Centers of Excellence in Artificial Intelligence and Machine Learning, emphasizing Research and Development collaboration, professional development, and community engagement.",
            "To create an open growth environment, producing Industry-ready graduates, and partnering globally in digital technical education.",
        ]
    ),

    page_break(),
    centered("PROGRAM OUTCOMES (POs)", "bold"),
    numbered(
        [
            "Engineering Knowledge: Apply knowledge of mathematics, natural science, computing, engineering fundamentals and an engineering specialization as specified in WK1 to WK4 respectively to develop to the solution of complex engineering problems.",
            "Problem Analysis: Identify, formulate, review research literature and analyze complex engineering problems reaching substantiated conclusions with consideration for sustainable development. (WK1 to WK4)",
            "Design/Development of Solutions: Design creative solutions for complex engineering problems and design/develop systems/components/processes to meet identified needs with consideration for the public health and safety, whole-life cost, net zero carbon, culture, society and environment as required. (WK5)",
            "Conduct Investigations of Complex Problems: Conduct investigations of complex engineering problems using research-based knowledge including design of experiments, modelling, analysis & interpretation of data to provide valid conclusions. (WK8)",
            "Engineering Tool Usage: Create, select and apply appropriate techniques, resources and modern engineering & IT tools, including prediction and modelling recognizing their limitations to solve complex engineering problems. (WK2 and WK6)",
            "The Engineer and the World: Analyze and evaluate societal and environmental aspects while solving complex engineering problems for its impact on sustainability with reference to economy, health, safety, legal framework, culture and environment. (WK1, WK5, WK7)",
            "Ethics: Apply ethical principles and commit to professional ethics, human values, diversity and inclusion; adhere to national & international laws. (WK9)",
            "Individual and Collaborative Team work: Function effectively as an individual, and as a member or leader in diverse/multi-disciplinary teams.",
            "Communication: Communicate effectively and inclusively within the engineering community and society at large, such as being able to comprehend and write effective reports and design documentation, make effective presentations considering cultural, language, and learning differences",
            "Project Management and Finance: Apply knowledge and understanding of engineering management principles and economic decision-making and apply these to one’s own work, as a member and leader in a team, and to manage projects and in multidisciplinary environments.",
            "Life-Long Learning: Recognize the need for, and have the preparation and ability for i) independent and life-long learning ii) adaptability to new and emerging technologies and iii) critical thinking in the broadest context of technological change. (WK8)",
        ]
    ),

    page_break(),
    centered("WASHINGTON ACCORD KNOWLEDGE PROFILES (WK)", "bold"),
    numbered(
        [
            "A systematic, theory-based understanding of the natural sciences applicable to the discipline and awareness of relevant social sciences.",
            "Conceptually-based mathematics, numerical analysis, data analysis, statistics and formal aspects of computer and information science to support detailed analysis and modelling applicable to the discipline.",
            "A systematic, theory-based formulation of engineering fundamentals required in the engineering discipline.",
            "Engineering specialist knowledge that provides theoretical frameworks and bodies of knowledge for the accepted practice areas in the engineering discipline; much is at the forefront of the discipline.",
            "Knowledge, including efficient resource use, environmental impacts, whole-life cost, reuse of resources, net zero carbon, and similar concepts, that supports engineering design and operations in a practice area.",
            "Knowledge of engineering practice (technology) in the practice areas in the engineering discipline.",
            "Knowledge of the role of engineering in society and identified issues in engineering practice in the discipline, such as the professional responsibility of an engineer to public safety and sustainable development.",
            "Engagement with selected knowledge in the current research literature of the discipline, awareness of the power of critical thinking and creative approaches to evaluate emerging issues.",
            "Ethics, inclusive behavior and conduct. Knowledge of professional ethics, responsibilities, and norms of engineering practice. Awareness of the need for diversity by reason of ethnicity, gender, age, physical ability etc. with mutual understanding and respect and of inclusive attitudes.",
        ]
    ),

    page_break(),
    centered("ABSTRACT", "bold"),
    spacer(6),
    p(
        "Conventional farm advisory systems separate crop-disease diagnosis, yield estimation, market intelligence and "
        "buyer discovery into disconnected tools. AgriTwin presents a unified, evidence-based digital-twin platform that "
        "keeps the farmer’s next decision at the centre while preserving the technical proof behind it. The deployed crop-health "
        "service uses a ConvNeXT-Tiny classifier with 38 classes and four-view test-time augmentation; it reports a class label "
        "and confidence together with Grad-CAM evidence, and a serving-only crop prior (alpha = 0.95) that is explicitly not used "
        "as a promotion baseline. Yield is estimated from historical state–crop production data and clearly flagged when a "
        "historical average is used. Live mandi prices are obtained from two official data.gov.in resources, deduplicated with the "
        "daily commodity resource preferred, and verified against the companion variety-wise resource; a clearly labelled keyless "
        "five-state mirror is the fallback. Transport values are estimates, and buyer offers are either user-created or explicitly "
        "marked as demo. A rule-based decision service ranks actions under the farmer’s cash, time and risk constraints and returns "
        "a short explanation plus linked evidence. The system was validated with 111 backend tests, 29 frontend tests, a successful "
        "production build and an API smoke check. AgriTwin demonstrates that real-data provenance and farmer-first usability can "
        "coexist in a transparent agricultural decision-support platform."
    ),
    p("**Keywords:** Digital Twin, Crop Health, ConvNeXT, Yield Prediction, Mandi Prices, data.gov.in, Decision Support, Explainable AI, Farmer-first Design"),

    page_break(),
    centered("TABLE OF CONTENTS", "bold"),
    spacer(6),
    table(
        "",
        ["Chapter", "Title", "Page No."],
        [
            ["1", "INTRODUCTION", "1"],
            ["2", "LITERATURE SURVEY", "2"],
            ["3", "SOFTWARE REQUIREMENTS", "3"],
            ["4", "SYSTEM DESIGN", "5"],
            ["5", "UML DIAGRAMS", "7"],
            ["6", "DISCUSSIONS", "11"],
            ["7", "SAMPLE CODE", "12"],
            ["8", "RESULTS", "14"],
            ["9", "CONCLUSION AND FUTURE SCOPE", "16"],
            ["", "REFERENCES", "17"],
            ["", "APPENDICES", "18"],
            ["", "INDEX", "19"],
        ],
        [0.8, 4.4, 1.0],
    ),
    p("Front matter: ACKNOWLEDGEMENT iii · ABSTRACT x · TABLE OF CONTENTS xi · LIST OF FIGURES xii · LIST OF TABLES xiii · ABBREVIATIONS xiv · COURSE OUTCOMES xv · CO-PO MAPPING xvi"),

    page_break(),
    centered("LIST OF FIGURES", "bold"),
    table(
        "Fig No. — Title — Page No.",
        ["Fig No.", "Title", "Page No."],
        [
            ["Fig 4.1", "System Architecture of AgriTwin", "5"],
            ["Fig 5.1", "Use Case Diagram of AgriTwin System", "7"],
            ["Fig 5.2", "Sequence Diagram of AgriTwin System", "8"],
            ["Fig 5.3", "Activity Diagram of AgriTwin System", "8"],
            ["Fig 5.4", "Class Diagram of AgriTwin System", "9"],
            ["Fig 5.5", "Component Diagram of AgriTwin System", "9"],
            ["Fig 5.6", "Deployment Diagram of AgriTwin System", "10"],
        ],
        [0.9, 4.3, 1.0],
    ),

    page_break(),
    centered("LIST OF TABLES", "bold"),
    table(
        "Table No. — Title — Page No.",
        ["Table No.", "Title", "Page No."],
        [
            ["Table CO-PO", "CO-PO Mapping for AgriTwin Project", "xvi"],
            ["Table 3.1", "Software Requirements", "3"],
            ["Table 3.2", "Hardware Requirements", "3"],
            ["Table 8.1", "Deployed Crop-Health Configuration", "14"],
            ["Table 8.2", "Verification Summary", "15"],
        ],
        [1.1, 4.1, 1.0],
    ),

    page_break(),
    centered("ABBREVIATIONS", "bold"),
    table(
        "",
        ["Abbreviation", "Full Form"],
        [
            ["AI", "Artificial Intelligence"],
            ["API", "Application Programming Interface"],
            ["CSS", "Cascading Style Sheets"],
            ["CSV", "Comma-Separated Values"],
            ["HTML", "HyperText Markup Language"],
            ["HTTP", "HyperText Transfer Protocol"],
            ["JS", "JavaScript"],
            ["JSON", "JavaScript Object Notation"],
            ["MAE", "Mean Absolute Error"],
            ["ML", "Machine Learning"],
            ["NLP", "Natural Language Processing"],
            ["REST", "Representational State Transfer"],
            ["R²", "Coefficient of Determination"],
            ["SHA", "Secure Hash Algorithm"],
            ["SQLite", "SQLite Database Engine"],
            ["TTA", "Test-Time Augmentation"],
            ["UI", "User Interface"],
            ["URL", "Uniform Resource Locator"],
        ],
        [1.4, 4.8],
    ),

    page_break(),
    centered("COURSE OUTCOMES (COs)", "bold"),
    table(
        "CO — Course Outcome Statement — Bloom’s Level",
        ["CO", "Course Outcome Statement", "Bloom’s Level"],
        [
            ["CO1", "Demonstrate the ability to synthesize and apply the knowledge and skills acquired in the academic program to real-world problems.", "L3 / L4 – Apply & Analyze"],
            ["CO2", "Evaluate different solutions based on economic and technical feasibility.", "L5 – Evaluate"],
            ["CO3", "Effectively plan a project and confidently perform all aspects of project management.", "L6 – Create"],
            ["CO4", "Demonstrate effective written and oral communication skills.", "L3 – Apply"],
        ],
        [0.6, 4.5, 1.1],
    ),

    page_break(),
    centered("CO-PO MAPPING", "bold"),
    table(
        "Table CO-PO : CO-PO Mapping",
        ["CO \\ PO", "PO1", "PO2", "PO3", "PO4", "PO5", "PO6", "PO7", "PO8", "PO9", "PO10", "PO11"],
        [
            ["CO1", "3", "3", "2", "-", "1", "1", "-", "2", "-", "1", "2"],
            ["CO2", "2", "2", "-", "2", "-", "2", "-", "-", "-", "3", "-"],
            ["CO3", "-", "1", "2", "-", "-", "1", "2", "3", "2", "3", "-"],
            ["CO4", "-", "-", "-", "-", "-", "-", "-", "2", "3", "-", "-"],
        ],
        [0.75] + [0.52] * 11,
    ),
    p("Correlation Level: 3 – High, 2 – Medium, 1 – Low, – – No Correlation"),
]

def build_body(figs: dict[str, str]) -> list:
    """Return the verified chapters, references, appendices and index."""
    return [
        # ------------------------------------------------------------------
        # CHAPTER 1 - INTRODUCTION
        # ------------------------------------------------------------------
        page_break(),
        centered("CHAPTER 1", "bold"),
        spacer(8),
        h1("INTRODUCTION"),
        h2("1.1 Introduction"),
        p(
            "The modern Indian smallholder combines several time-sensitive signals before taking a single marketing "
            "decision: a mandi price from yesterday, a buyer’s phone offer, an uncertain yield expectation, a possible "
            "leaf disease, and the distance to a purchaser. These signals usually arrive in different formats and are "
            "reasoned about separately. AgriTwin is a full-stack, evidence-based digital-twin platform that brings them "
            "into one auditable decision: **should the farmer sell now, wait, or inspect the crop first?**"
        ),
        p(
            "The platform was built as a B.Tech CSE (AI & ML) major project using a React 18 + TypeScript frontend, a "
            "FastAPI backend, trained PyTorch and scikit-learn models, SQLAlchemy 2 persistence with Alembic, SQLite for "
            "development and PostgreSQL 16 under Docker Compose. The decision is produced by a deterministic, explainable "
            "rule engine rather than a generative prompt, so every recommendation can be traced back to inputs, policy "
            "thresholds and source freshness."
        ),
        p(
            "AgriTwin deliberately keeps the farmer-facing result simple while preserving the technical evidence behind "
            "it. The default view answers the decision first; live rates, model versions, uncertainty intervals, source "
            "licences and test-time augmentation details remain available behind an explicit data-details control. No "
            "synthetic price is ever presented as real. User-created buyer records are live; seeded records are labelled "
            "as demo, and transport figures are shown as estimates unless a route was actually resolved."
        ),
        h2("1.2 Motivation"),
        p("The motivation for AgriTwin comes from five documented limitations of existing farm-advisory workflows:"),
        bullets(
            [
                "**Fragmented evidence:** price, disease, yield and transport information is scattered across separate tools with no auditable fusion method.",
                "**Hidden uncertainty:** a single predicted number hides the interval around a yield or price estimate, so farmers cannot judge risk.",
                "**Domain shift:** a high laboratory accuracy does not guarantee reliability on real field photographs.",
                "**Opaque advice:** recommendations are often presented without rules, assumptions or missing-input warnings.",
                "**Weak provenance:** users cannot easily tell whether a price is official, cached, stale, estimated or demo data.",
            ]
        ),
        p(
            "AgriTwin responds by quantifying uncertainty with yield and price intervals, fusing eight weighted risk "
            "components with completeness and freshness checks, applying ordered rules from a versioned JSON policy, and "
            "returning an explanation with every decision. The guiding principle is that a farmer should receive one clear "
            "next action, while an evaluator should still be able to inspect the complete evidence chain."
        ),

        # ------------------------------------------------------------------
        # CHAPTER 2 - LITERATURE SURVEY
        # ------------------------------------------------------------------
        page_break(),
        centered("CHAPTER 2", "bold"),
        spacer(8),
        h1("LITERATURE SURVEY"),
        h2("2.1 Review of Literature"),
        p(
            "Image-based plant disease detection was established by Mohanty, Hughes and Salathé, who showed that deep "
            "convolutional networks can classify leaf images at high accuracy on controlled PlantVillage data while "
            "noting the limited realism of laboratory conditions. Subsequent work adopted transfer learning with "
            "EfficientNet, ResNet and MobileNet backbones, generally reporting in-domain accuracy and paying less "
            "attention to field transfer."
        ),
        p(
            "PlantDoc was introduced by Singh et al. as a dataset of disease symptoms in the wild. Its photographs expose "
            "background shortcuts and single-label limits that do not appear in controlled datasets. Grad-CAM, proposed "
            "by Selvaraju et al., is used in AgriTwin to check whether a prediction attends to lesions rather than "
            "irrelevant background. Digital-twin thinking is supported by Kim and Heo’s work on individualized mandarin "
            "agriculture, while conformal prediction motivates distribution-free yield intervals."
        ),
        p(
            "Regressors for market and yield forecasting were compared empirically rather than assumed: SeasonalNaive, "
            "MovingAverage, LinearTrendWeekly, RandomForest and GradientBoosting candidates are scored on chronological "
            "tail validation before a winner is refitted. This avoids using future observations to justify a forecast."
        ),
        h2("2.2 Summary And Research Gaps"),
        h3("2.2.1 Summary"),
        p(
            "The literature shows progress in image classification, field datasets, explainability and digital twins, but "
            "these strands are usually evaluated separately. A farmer still has to combine a disease score, a yield "
            "estimate, a mandi quote and a buyer offer without a transparent method for weighting them."
        ),
        h3("2.2.2 Research Gap"),
        p("The measured gaps that motivated AgriTwin are:"),
        bullets(
            [
                "A historical EfficientNet-B0 lab-only model reached 0.9549 on PlantVillage but only 0.3220 on PlantDoc — a 63.3-point collapse that makes lab-only reporting misleading.",
                "Two-stage adaptation underperformed joint training on both domains (0.8308 lab / 0.5551 field), an honest negative result preserved in the project evidence.",
                "Most advisory tools expose raw numbers or opaque recommendations rather than an explainable SELL / WAIT / INSPECT decision.",
                "The classifier covers 38 labels over 14 crop species; unsupported crops are still forced into a trained label, so output is screening support, not diagnosis.",
                "The yield dataset has no paired soil, weather, irrigation or fertiliser records, so those features are absent rather than invented.",
                "The bundled Agmarknet market window covers 2026-07-02 to 2026-09-24; annual seasonality cannot be learned and Sugarcane has only 7 observations, below the 21-observation forecast minimum.",
                "Market forecasting does not use arrivals, rainfall, fuel prices or policy events, and OSRM routing has no automated test coverage in the documented suite.",
            ]
        ),
        p(
            "AgriTwin addresses these gaps with a unified pipeline that keeps uncertainty, provenance and ordered rules "
            "visible while presenting a single farmer-first decision."
        ),

        # ------------------------------------------------------------------
        # CHAPTER 3 - SOFTWARE REQUIREMENTS
        # ------------------------------------------------------------------
        page_break(),
        centered("CHAPTER 3", "bold"),
        spacer(8),
        h1("SOFTWARE REQUIREMENTS"),
        h2("3.1 Description Of Software Requirements"),
        p(
            "A System Requirements Specification for AgriTwin defines how the React client, FastAPI services, machine "
            "learning inference modules and persistence layer interact to turn farm data and verified external signals "
            "into an auditable decision."
        ),
        h2("3.2 Operational Requirements"),
        h3("3.2.1 Software Requirements"),
        table(
            "Table 3.1: Software Requirements",
            ["Area", "Requirement"],
            [
                ["Operating System", "Windows 10/11, Ubuntu Linux or macOS"],
                ["Programming Languages", "Python 3.12 (backend and ML); TypeScript with React 18 (frontend)"],
                ["Backend Framework", "FastAPI, Pydantic v2, Uvicorn"],
                ["Frontend", "Vite, React Router, TanStack Query, React Hook Form, Zod, Recharts, Lucide, Tailwind CSS"],
                ["ML Libraries", "PyTorch (ConvNeXT-Tiny, Grad-CAM), scikit-learn (ExtraTrees, conformal intervals)"],
                ["Persistence", "SQLAlchemy 2, Alembic, SQLite for development, PostgreSQL 16 for Docker"],
                ["Official Data", "data.gov.in Agmarknet resources A1 and A2, keyless five-state mirror fallback"],
                ["External APIs", "Open-Meteo weather/geocoding, OSRM routing, Google Gemini advisor (optional)"],
                ["Operations", "Docker Compose, nginx, structured JSON logging, request IDs, rate limiting, CORS"],
                ["Testing", "pytest (backend), Vitest (frontend), API and Docker smoke scripts"],
            ],
            [1.6, 4.4],
        ),
        h3("3.2.2 Hardware Requirements"),
        table(
            "Table 3.2: Hardware Requirements",
            ["Component", "Requirement"],
            [
                ["Processor", "Dual-core Intel Core i5 / AMD Ryzen 5; quad-core i7 / Ryzen 7 recommended"],
                ["RAM", "8 GB minimum; 16 GB recommended for training experiments"],
                ["GPU", "Integrated graphics sufficient for serving; RTX 5060 used for v3 training with AMP"],
                ["Storage", "10 GB SSD minimum; 20 GB recommended for datasets and local model artifacts"],
                ["Network", "Broadband internet for official APIs, weather, routing and optional Gemini access"],
            ],
            [1.5, 4.5],
        ),
        h2("3.3 Functional Requirements"),
        bullets(
            [
                "**Authentication and ownership:** register, login, refresh, logout and update profile. JWT access and refresh tokens use bcrypt hashing, rotation and revocation; farm-scoped failures return 403 and service-scoped lookups return 404.",
                "**Farm and crop management:** create, read, update and delete farms and crops with Indian states, seasons, soil types, growth stages, harvest dates and coordinates.",
                "**Crop health:** upload a leaf image with MIME, 8 MB size, 4096 px dimension and SHA-256 dedupe checks; return a 38-class label, confidence, severity, advisory text and Grad-CAM overlay with explicit real/demo labelling.",
                "**Yield prediction:** estimate yield in quintals per hectare and total quintals from crop, season, state, area and historical means; attach an 80% conformal interval and flag historical-average fallback.",
                "**Market intelligence:** expose live official rates, bundled Agmarknet history, trends, on-demand forecasts, empirical 80% intervals and authenticated CSV import.",
                "**Buyer and offer management:** maintain buyers, quantity-constrained offers and expiry constraints, then evaluate eligibility against the decision request.",
                "**Transport and weather:** estimate cost from vehicle profiles using OSRM when available, otherwise geodesic distance × 1.25 with distance_method='approximate'; cache Open-Meteo weather and degrade gracefully to an unavailable state.",
                "**Decision engine:** resolve yield, health, price, buyer, harvest and weather inputs; run policy version 1.0.1; return SELL / WAIT / INSPECT with scenarios, revenue bounds, factors, assumptions and missing inputs.",
                "**Dashboard and reports:** aggregate farm signals, persist decisions and generate downloadable JSON reports.",
                "**System status:** report model mode, version, metrics and data freshness so the UI and operators can see exactly what is running.",
            ]
        ),
        h2("3.4 Non-Functional Requirements"),
        bullets(
            [
                "**Performance:** the frontend build passes; crop-health serving benchmarks at 31.9 ms per image for one forward pass at batch 1 and 231.4 images/s at batch 32. Four-view serving measured about 1.76 s per CPU prediction in the smoke run.",
                "**Accuracy:** deployed crop-health unconstrained 4-view field accuracy is 0.7161 with macro-F1 0.7093; serving crop prior raises field accuracy to 0.8093 but is not a promotion metric. Yield held-out R² is 0.9533 with 80% interval coverage 0.8492.",
                "**Accessibility:** farmer-first pages show one clear decision first; technical provenance sits behind View data details. High-contrast warnings and plain-language labels support non-technical users.",
                "**Scalability:** services are isolated behind routers and service modules; Docker Compose separates PostgreSQL, backend and nginx. Optional live sources can be disabled without changing the core API.",
                "**Reliability:** A2 variety-source failures degrade to A1-only, A1 failures keep the keyless mirror, weather failure applies a 0.40 risk floor, and invalid uploads are rejected before inference.",
                "**Security:** JWT expiry defaults to 60 minutes for access and 7 days for refresh; rate limits are 120 requests/minute and 20 for auth; CORS origins are explicit; production relies on Alembic rather than create_all.",
                "**Maintainability:** decision rules live in versioned JSON; model metadata drives TTA and prior behaviour; structured logs carry request IDs and error envelopes carry code, message, details and request_id.",
            ]
        ),

        # ------------------------------------------------------------------
        # CHAPTER 4 - SYSTEM DESIGN
        # ------------------------------------------------------------------
        page_break(),
        centered("CHAPTER 4", "bold"),
        spacer(8),
        h1("SYSTEM DESIGN"),
        h2("4.1 System Architecture"),
        figure("Fig 4.1: System Architecture of AgriTwin", figs["architecture"]),
        p("AgriTwin is organised into seven architectural layers:"),
        numbered(
            [
                "**Data layer:** curated public datasets, seed records and validated uploads.",
                "**Persistence layer:** SQLAlchemy 2 models, Alembic migrations, SQLite in development and PostgreSQL 16 in Docker.",
                "**ML / inference layer:** ConvNeXT-Tiny with 4-view TTA and Grad-CAM, ExtraTrees with split-conformal intervals, and chronological market forecasters.",
                "**Decision layer:** policy → risk → fusion → ordered rules, implemented in pure Python with Decimal money arithmetic.",
                "**Service / orchestration layer:** auth, farms, crop-health, yield, market, buyers, transport, weather, decisions, dashboard, reports and crop calendar.",
                "**API layer:** FastAPI routers under /api/v1 with Pydantic v2 models, JWT dependencies, rate limiting and a unified error envelope.",
                "**Presentation layer:** a React 18 + TypeScript single-page application with protected pages, forms, charts and an auth context.",
            ]
        ),
        h2("4.2 System Workflow"),
        h3("4.2.1 Crop-health scan"),
        p(
            "The client posts an image to /api/v1/crop-health/predict. After authentication, ownership checks and upload "
            "validation, the service preprocesses four views (resize 240/216, centre crop 192, ImageNet normalise), "
            "averages softmax probabilities, applies the optional crop prior, generates a Grad-CAM overlay and persists the "
            "prediction. The response includes the label, confidence, severity, model_mode and gradcam_url."
        ),
        h3("4.2.2 Yield and market forecast"),
        p(
            "Yield features are crop, season, state, area, log_area and expanding historical means; the prediction is "
            "scaled by area and bounded by a conformal interval. Market forecasting selects a market with enough daily "
            "observations, requires at least 21 valid rows, compares five candidates on a chronological tail, refits the "
            "winner and widens the empirical residual interval by the square root of the forecast step."
        ),
        h3("4.2.3 Decision generation"),
        p(
            "The decision service resolves or auto-computes all required inputs, builds a DecisionInput, calls decide() "
            "from the pure engine, persists DecisionResult and DecisionFactor rows, and returns the action with its "
            "explanation. The first matching rule wins, so the result is reproducible from the stored policy version."
        ),

        # ------------------------------------------------------------------
        # CHAPTER 5 - UML DIAGRAMS
        # ------------------------------------------------------------------
        page_break(),
        centered("CHAPTER 5", "bold"),
        spacer(8),
        h1("UML DIAGRAMS"),
        h2("5.1 Use Case Diagram"),
        p(
            "The authenticated farmer can manage farms and crops, upload a leaf photo and view the health result, request "
            "a yield interval, inspect live mandi rates and forecasts, manage buyers and offers, estimate transport, view "
            "weather risk, generate decisions, read the dashboard, download reports and inspect system status."
        ),
        figure("Fig 5.1: Use Case Diagram of AgriTwin System", figs["usecase"]),
        h2("5.2 Sequence Diagram"),
        p(
            "The sequence combines a crop-health scan with a decision request. The React page calls the authenticated API, "
            "the service layer runs inference and evidence resolution, and the pure decision engine returns an explained "
            "outcome that the frontend renders as one clear action."
        ),
        figure("Fig 5.2: Sequence Diagram of AgriTwin System", figs["sequence"]),
        h2("5.3 Activity Diagram"),
        p(
            "Decision rules are applied in order: diseased scan with high severity or low confidence → INSPECT; not "
            "harvest-ready → WAIT; completeness below 0.60 → INSPECT; relative yield interval above 0.50 → INSPECT; price "
            "older than 90 days → INSPECT; risk above the preference cap → INSPECT; wait scenario recommended → WAIT; "
            "positive immediate net realisation → SELL; otherwise INSPECT."
        ),
        figure("Fig 5.3: Activity Diagram of AgriTwin System", figs["activity"]),
        h2("5.4 Class Diagram"),
        p(
            "Core objects include FarmerProfile, CropHealthResult, LiveRatesResponse, DecisionRequest, DecisionService and "
            "EvidenceBundle. Persistence classes include User, Farm, Crop, UploadedFile, Buyer, BuyerOffer, MarketPriceRecord, "
            "YieldPrediction, CropHealthPrediction, DecisionResult, DecisionFactor and Report."
        ),
        figure("Fig 5.4: Class Diagram of AgriTwin System", figs["class"]),
        h2("5.5 Component Diagram"),
        p(
            "The presentation components call FastAPI routers; routers delegate to crop-health, market, decision and other "
            "services; ML modules supply inference; and SQLite/PostgreSQL plus the cache hold state. External systems "
            "include data.gov.in, Open-Meteo and OSRM."
        ),
        figure("Fig 5.5: Component Diagram of AgriTwin System", figs["component"]),
        h2("5.6 Deployment Diagram"),
        p(
            "Local development uses SQLite, Uvicorn on port 8000 and Vite on port 5173. Docker Compose adds a PostgreSQL 16 "
            "container, a backend container that runs alembic upgrade head before Uvicorn, and an nginx container that serves "
            "the built SPA and proxies /api and /uploads."
        ),
        figure("Fig 5.6: Deployment Diagram of AgriTwin System", figs["deployment"]),

        # ------------------------------------------------------------------
        # CHAPTER 6 - DISCUSSIONS
        # ------------------------------------------------------------------
        page_break(),
        centered("CHAPTER 6", "bold"),
        spacer(8),
        h1("DISCUSSIONS"),
        h2("6.1 Data Sources & Knowledge Integration"),
        bullets(
            [
                "**Crop health:** PlantVillage subset (1,900 images, 38 classes: 1,368 train / 266 val / 266 test) and PlantDoc (2,572 recovered files, 236 official field test images) are jointly handled through a leakage-free manifest of 4,460 entries after removing 11 byte-identical train/test leaks.",
                "**Yield:** the district-level crop production dataset contains 246,091 rows from 1997–2015; the target is yield_q_per_ha = production_tonnes × 10 / area_ha. A 3,000-row 2010–2015 sample supports regional comparison.",
                "**Market:** the bundled Agmarknet archive has 2,229 rows for 14 crops from 2026-07-02 to 2026-09-24. Live rates use official resource A1 (9ef84268-d588-465a-a308-a864a43d0070) and variety-wise companion A2 (35985678-0d79-46b4-9ed6-6f13308a1d24).",
                "**Decision knowledge:** config/decision_policy.json version 1.0.1 defines eight risk weights that sum to 1.0, ordered rules, channel economics and freshness limits.",
                "**External context:** Open-Meteo supplies weather and geocoding; OSRM supplies routes; Gemini supplies optional conversational explanations. Each has a labelled degradation path.",
            ]
        ),
        h2("6.2 Official API Integration and Dedupe"),
        p(
            "GET /api/v1/market/live-rates merges A1 and A2, deduplicates by date, state, district, market, commodity, "
            "variety and grade, prefers A1 for duplicate rows, and reserves up to half the requested limit for unique A2 "
            "rows. A2 is queried with sort[Arrival_Date]=desc because its default order is oldest first. A2 failures degrade "
            "to A1-only; LIVE_MARKET_USE_VARIETY_SOURCE=false disables A2 explicitly. The response reports provider, source "
            "URLs, licence, observation date and freshness."
        ),
        h2("6.3 Real, Demo and Degraded Modes"),
        p(
            "Real and demo states are never silent. model_mode, is_demo, model_version and distance_method are returned by "
            "the API and surfaced in the UI. Seeded buyer offers are demo records; the keyless five-state mirror is labelled "
            "rather than presented as the official feed; historical-average yield is flagged; geodesic transport is labelled "
            "approximate; and Gemini failure falls back to a local rule-based advisor."
        ),
        h2("6.4 Model Change Control"),
        p(
            "The deployed crop-health artifact is crop-health-v3.0.0-convnext and remains unchanged. Post-v3 candidates were "
            "rejected when their unconstrained 4-view field accuracy failed to strictly beat 0.7161. PlantTom variants scored "
            "0.6864, 0.6695 and 0.6864; the Zenodo continued candidate scored 0.6822. No retraining or promotion is claimed "
            "in this report."
        ),

        # ------------------------------------------------------------------
        # CHAPTER 7 - SAMPLE CODE
        # ------------------------------------------------------------------
        page_break(),
        centered("CHAPTER 7", "bold"),
        spacer(8),
        h1("SAMPLE CODE"),
        h2("7.1 Application Factory and Middleware — backend/app/main.py"),
        code(
            "1. Application lifespan and middleware registration",
            r'''@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (settings.UPLOAD_DIR / "gradcam").mkdir(parents=True, exist_ok=True)
    if settings.ENVIRONMENT != "production":
        Base.metadata.create_all(bind=engine)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware)
register_exception_handlers(app)
app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")
app.include_router(api_router, prefix=settings.API_V1_PREFIX)''',
        ),
        h2("7.2 Decision API and Service Bridge"),
        code(
            "2. Decision route and input construction",
            r'''@router.post("", response_model=DecisionOut, status_code=status.HTTP_201_CREATED)
def create_decision(payload: DecisionRequest, user: CurrentUser, db: DbSession) -> DecisionOut:
    _row, output = decision_service.run(db, user, payload)
    return output''',
        ),
        code(
            "3. Pure engine call inside backend/app/services/decision_service.py",
            r'''inputs = DecisionInput(
    today=date.today(), farm_id=farm.id, crop_id=crop.id,
    crop_name=crop.crop_name, quantity_quintals=quantity,
    yield_info=yield_info, health_info=health_info,
    price_info=price_info, buyers=buyer_inputs,
    harvest_info=harvest_info, risk_preference=request.risk_preference,
    weather_risk=weather_risk, weather_available=weather_available,
    transport_available=any(b.has_coordinates for b in buyer_inputs),
)
policy = get_policy()
outcome = decide(inputs, policy)''',
        ),
        h2("7.3 Crop-Health TTA and Crop Prior"),
        code(
            "4. Four-view averaging and soft prior — backend/app/ml/crop_health/service.py",
            r'''def tta_probabilities(model, model_meta, image, views=1, device=None):
    probabilities, base_tensor = tta_view_probabilities(
        model, model_meta, image, views, device
    )
    return torch.stack(probabilities).mean(dim=0), base_tensor

adjusted = probabilities * (1.0 - alpha + alpha * mask)
adjusted = adjusted / adjusted.sum()
return adjusted, group, float(alpha)''',
        ),
        h2("7.4 Yield and Market Inference"),
        code(
            "5. Conformal bounds — backend/app/ml/yield_prediction/inference.py",
            r'''prediction = float(model.predict(features)[0])
prediction = max(prediction, 0.0)
lower = max(prediction - half_width, 0.0)
upper = max(prediction + half_width, prediction)''',
        ),
        code(
            "6. Chronological validation — backend/app/ml/market_forecasting/forecast.py",
            r'''LAGS = [1, 2, 3, 7, 14, 21, 28]
MIN_OBSERVATIONS = 21

test_days = min(max(7, len(series) // 5), 21, len(series) - 14)
train = series.iloc[:-test_days]
actual = series.iloc[-test_days:].to_numpy()''',
        ),
        h2("7.5 Official Live-Rate Adapter"),
        code(
            "7. Provider selection — backend/app/services/live_market.py",
            r'''OFFICIAL_SOURCE_NAME = "Agmarknet / data.gov.in"
KEYLESS_LICENSE = "CC BY-NC-SA 4.0 (Mandi Price API); source data: Agmarknet/data.gov.in"
VARIETY_SOURCE_NAME = "Agmarknet / data.gov.in - Variety-wise Daily Market Prices"

if provider == "mandi_api":
    payload = _fetch_keyless(client, crop=crop, state=state, market=market, limit=limit)
else:
    try:
        payload = _fetch_official(client, crop=crop, state=state, market=market, limit=limit)''',
        ),
        h2("7.6 Frontend Auth Refresh — frontend/src/lib/api.ts"),
        code(
            "8. Automatic refresh on 401",
            r'''export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, rawBody, auth = true, headers, ...rest } = options;

  if (response.status === 401 && auth) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      response = await execute();
    } else {
      clearTokens();
    }
  }''',
        ),

        # ------------------------------------------------------------------
        # CHAPTER 8 - RESULTS
        # ------------------------------------------------------------------
        page_break(),
        centered("CHAPTER 8", "bold"),
        spacer(8),
        h1("RESULTS"),
        h2("8.1 System Output and Evaluation"),
        p(
            "The deployed crop-health artifact and all reported metrics were read from the checked model metadata and "
            "evaluation results. No unapproved experiment is presented as deployed."
        ),
        table(
            "Table 8.1: Deployed Crop-Health Configuration",
            ["Field", "Verified Value"],
            [
                ["Version", "crop-health-v3.0.0-convnext"],
                ["Architecture", "convnext_tiny, ImageNet-V1 pre-trained"],
                ["Classes / crop species", "38 classes over 14 crop species"],
                ["Training mode", "mixed — PlantVillage + PlantDoc jointly"],
                ["Input", "192 × 192 centre crop from resize 240; ImageNet mean/std"],
                ["Seed / precision", "seed 42; AMP enabled; 12 epochs; 1,602 s"],
                ["Artifact", "backend/app/ml/artifacts/crop_health/model.pt; 111,452,123 bytes"],
                ["SHA-256", "4500C4FF14C99D3E7AFEC2F838AA555BADB3809656227CE77340391F14BD3A75"],
                ["Serving metadata", "tta_views=4; crop_prior_alpha=0.95"],
            ],
            [1.7, 4.3],
        ),
        table(
            "Crop-health accuracy by inference mode (modes kept separate)",
            ["Mode", "Lab", "Field", "Field macro-F1", "Interpretation"],
            [
                ["Single view", "0.9774", "0.6907", "0.6833", "Strictly beat the earlier 0.6780 baseline; separate from 4-view."],
                ["4-view TTA, unconstrained", "0.9812", "0.7161", "0.7093", "Promotion / serving baseline; post-v3 gate requires strictly beating this."],
                ["4-view TTA + crop prior", "0.9850", "0.8093", "0.8024", "Deployed serving result only; not a promotion baseline."],
            ],
            [1.35, 0.7, 0.7, 1.0, 2.25],
        ),
        p(
            "The PlantDoc field test contains 236 images and PlantVillage has 266 test images. Four-view TTA fixed 9 images "
            "and broke 3 relative to the promoted single-view model; accuracy below 0.55 confidence improved from 0.3333 to "
            "0.4167 on n=48. CUDA and CPU TTA both returned 0.7161. The 0.8093 figure comes from a serving-only soft crop "
            "prior (alpha = 0.95) that reweights probabilities only when the farm crop maps to a trained group; wrong-hint "
            "checks gave 0.8008 at 5% wrong, 0.8051 at 10% and 0.7754 at 20%. A hard prior was rejected."
        ),
        h2("8.2 Yield, Market and Decision Results"),
        bullets(
            [
                "**Yield (yield-v1.0.0):** chronological test on 2015 rows (305) gave MAE 14.7151 q/ha, RMSE 36.5968 q/ha, R² 0.9533 and MAPE 57.52%. The 80% conformal interval achieved 0.8492 coverage with mean half-width 17.4339 q/ha. MAPE is reported intentionally because skewed small-denominator rows inflate it.",
                "**Market forecasters:** five candidates were compared by chronological tail MAE; the winner was refitted on full history. Empirical absolute residual 80th-percentile intervals were widened by √step and floored at ₹1. Sugarcane returned 422 insufficient_data with only 7 observations.",
                "**Live-rate verification (2026-11-25):** all 14 supported crops and all five South India filter states returned provider=data_gov, is_demo=false, latest_observation_date=2026-11-25 and 0-day freshness, with rows from both A1 and A2 at limit 5. The Agriculture APIs catalogue showed 146 active resources.",
                "**Decision engine:** policy version 1.0.1, eight weights summing to 1.0, 17 engine unit tests and 6 API tests. A Docker smoke example returned SELL via mandi with net realisation ₹6,371.67/quintal and medium risk 0.44; this is a historical data-dependent example, not a current price claim.",
            ]
        ),
        table(
            "Table 8.2: Verification Summary",
            ["Check", "Command / Evidence", "Result"],
            [
                ["Backend tests", "python -m pytest -q --disable-warnings", "111 passed"],
                ["Frontend tests", "npm test -- --run", "29 passed"],
                ["Production build", "npm run build", "passed; chunk-size warning only"],
                ["API smoke", "python scripts\\smoke_api.py", "passed with real ConvNeXt + TTA + Grad-CAM"],
                ["Docker smoke", "python scripts\\smoke_docker.py", "passed 2026-11-04; daemon unavailable for re-run here"],
                ["Migrations", "alembic upgrade → downgrade → upgrade", "verified on SQLite"],
                ["Live official feed", "GET /api/v1/market/live-rates", "14/14 crops and 5/5 states, 0-day freshness"],
            ],
            [1.2, 2.7, 2.1],
        ),
        p(
            "Ad-hoc web photo checks were treated only as smoke evidence: five downloaded photos gave 2/5 exact matches "
            "(3/5 if crop mismatch is ignored) and two low-confidence results routed to INSPECT. They are not a labelled "
            "evaluation set and were never used for training."
        ),

        # ------------------------------------------------------------------
        # CHAPTER 9 - CONCLUSION AND FUTURE SCOPE
        # ------------------------------------------------------------------
        page_break(),
        centered("CHAPTER 9", "bold"),
        spacer(8),
        h1("CONCLUSION & FUTURE SCOPE"),
        h2("9.1 Conclusion"),
        p(
            "AgriTwin is a working, tested, documented and containerised full-stack platform that connects real datasets "
            "and trained models to a farmer’s next decision. Its central contribution is a deterministic, explainable and "
            "uncertainty-aware decision engine that returns SELL, WAIT or INSPECT with reproducible factors and source "
            "freshness, rather than an opaque recommendation."
        ),
        p(
            "The platform honestly surfaces its boundaries: field domain shift, a short bundled market window, high yield "
            "MAPE from skewed small-denominator rows, missing soil/weather yield features, labelled demo records and "
            "degraded external-service modes. Deployed crop-health remains crop-health-v3.0.0-convnext; no further "
            "retraining or artifact promotion is claimed. By keeping farmer-first simplicity on the surface and complete "
            "evidence underneath, AgriTwin shows that trustworthy AI assistance and practical usability can coexist."
        ),
        h2("9.2 Future Scope"),
        bullets(
            [
                "Add soil, weather and irrigation features to the yield model using paired district-level weather joins.",
                "Extend market history to multiple years and add arrivals, rainfall and policy-event features.",
                "Add browser-driven Playwright/Cypress tests and OSRM integration tests with a local routing container.",
                "Add Hindi and Marathi localisation plus voice input for low-literacy users.",
                "Integrate real buyer channels and logistics booking behind the existing service interfaces.",
                "Calibrate decision policy with farmer field trials and track realised outcomes against recommendations.",
                "Continue field-focused crop-health research with domain adaptation; treat screening output as support, not diagnosis.",
                "Explore on-device deployment, multi-label disease/severity modelling and active learning from verified farmer feedback.",
            ]
        ),

        # ------------------------------------------------------------------
        # REFERENCES
        # ------------------------------------------------------------------
        page_break(),
        h1("REFERENCES"),
        numbered(
            [
                "Mohanty, S. P., Hughes, D. P., and Salathé, M. “Using Deep Learning for Image-Based Plant Disease Detection.” Frontiers in Plant Science, vol. 7, p. 1419, 2016, doi: 10.3389/fpls.2016.01419.",
                "Singh, D., Jain, N., Jain, P., Kayal, P., Kumawat, S., and Batra, N. “PlantDoc: A Dataset for Visual Plant Disease Detection.” ACM CoDS-COMAD, pp. 249–253, 2020, doi: 10.1145/3371158.3371196.",
                "Tan, M., and Le, Q. “EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks.” ICML, 2019.",
                "Selvaraju, R. R., Cogswell, M., Das, A., Vedantam, R., Parikh, D., and Batra, D. “Grad-CAM: Visual Explanations from Deep Networks via Gradient-Based Localization.” ICCV, pp. 618–626, 2017, doi: 10.1109/ICCV.2017.74.",
                "Kim, S., and Heo, S. “An agricultural digital twin for mandarins demonstrates the potential for individualized agriculture.” Nature Communications, vol. 15, p. 1561, 2024, doi: 10.1038/s41467-024-45812-1.",
                "Government of India, Ministry of Agriculture and Farmers Welfare. “Current Daily Price of Various Commodities from Various Markets (Mandi).” data.gov.in resource 9ef84268-d588-465a-a308-a864a43d0070.",
                "Government of India, Directorate of Marketing and Inspection. “Variety-wise Daily Market Prices Data of Commodity.” data.gov.in resource 35985678-0d79-46b4-9ed6-6f13308a1d24.",
                "Open-Meteo. Weather and geocoding API documentation. https://open-meteo.com/",
                "OSRM. Open Source Routing Machine public demo server documentation. http://project-osrm.org/",
                "PlantVillage subset: Hemg/new-plant-diseases-dataset on Hugging Face; PlantDoc: github.com/pratikkayal/PlantDoc-Dataset (CC BY 4.0); Agmarknet archive: github.com/kunal-rajput-317/mandi-data (CC BY 4.0).",
            ]
        ),

        # ------------------------------------------------------------------
        # APPENDICES
        # ------------------------------------------------------------------
        page_break(),
        h1("APPENDICES"),
        h2("Appendix I — Sample Decision Output JSON"),
        code(
            "Illustrative structure from a verified decision response",
            r'''{
  "action": "SELL",
  "channel": "mandi",
  "confidence": 0.78,
  "risk_score": 0.44,
  "risk_band": "medium",
  "net_realisation_per_quintal": 6371.67,
  "revenue_interval": [318583.50, 397920.40],
  "factors": [
    {"name": "price_freshness", "value": 0.93},
    {"name": "buyer_offer", "value": 0.71},
    {"name": "crop_health", "value": 0.66}
  ],
  "assumptions": ["market series contains at least 21 observations"],
  "missing_inputs": [],
  "policy_version": "1.0.1"
}''',
        ),
        p("The numeric values above illustrate the schema from a historical smoke example and are not current market quotes."),
        h2("Appendix II — System Installation & Developer Setup Guide"),
        numbered(
            [
                "**Prerequisite verification:** install Python 3.12, Node.js 20+ and npm. Docker Desktop is optional but required for the PostgreSQL/nginx stack.",
                "**Repository clone:** git clone https://github.com/Jashwanth1827/AgriTwin.git and change into AgriTwin.",
                "**Backend environment:** create a virtual environment, activate it, run pip install -r backend/requirements.txt and pip install -r backend/requirements-dev.txt.",
                "**Frontend environment:** run npm install inside frontend/.",
                "**Configuration:** create .env from .env.example. Set DATA_GOV_API_KEY only for a deployment-specific key; never commit it. Optional flags include LIVE_MARKET_PROVIDER=auto, LIVE_MARKET_USE_VARIETY_SOURCE=true and EXTERNAL_CACHE_TTL_SECONDS=900.",
                "**Database:** run alembic upgrade head from backend/. Production does not call create_all.",
                "**Backend start:** run uvicorn app.main:app --reload; the API is available at http://localhost:8000 and docs at /docs.",
                "**Frontend start:** run npm run dev; the UI is available at http://localhost:5173 and Vite proxies /api and /uploads to port 8000.",
                "**Verification:** run python -m pytest -q --disable-warnings, npm test -- --run, npm run build and python scripts\\smoke_api.py.",
            ]
        ),
        code(
            "Example .env entries (no secret values)",
            r'''DATA_GOV_API_KEY=your_deployment_specific_key_here
LIVE_MARKET_PROVIDER=auto
LIVE_MARKET_USE_VARIETY_SOURCE=true
EXTERNAL_CACHE_TTL_SECONDS=900
LIVE_MARKET_TIMEOUT_SECONDS=30.0''',
        ),

        # ------------------------------------------------------------------
        # INDEX
        # ------------------------------------------------------------------
        page_break(),
        h1("INDEX"),
        table(
            "",
            ["Term", "Page No.", "Term", "Page No."],
            [
                ["Activity Diagram", "8", "Machine Learning", "3, 14"],
                ["AI Advisor / Gemini", "3", "Mean Absolute Error", "14"],
                ["Artificial Intelligence", "xiv", "Model Change Control", "11"],
                ["Class Diagram", "9", "Open-Meteo", "3"],
                ["Crop Health", "3, 14", "Prediction Pipeline", "12"],
                ["Decision Engine", "3, 12", "Program Outcomes", "viii"],
                ["Deployment Diagram", "10", "Real vs Demo", "11"],
                ["Digital Twin", "1", "Sequence Diagram", "8"],
                ["Functional Requirements", "3", "Software Requirements", "3"],
                ["Grad-CAM", "3, 14", "SQLite Database", "5"],
                ["Hardware Requirements", "3", "System Architecture", "5"],
                ["Introduction", "1", "System Workflow", "5"],
                ["Keyless Fallback", "11", "Test-Time Augmentation", "14"],
                ["Live Mandi Rates", "3, 15", "UML Diagrams", "7"],
                ["CO-PO Mapping", "xvi", "Use Case Diagram", "7"],
                ["Component Diagram", "9", "Yield Prediction", "3, 14"],
                ["Course Outcomes", "xv", "", ""],
            ],
            [1.8, 0.8, 1.9, 0.8],
        ),
    ]


def main() -> None:
    figs = make_diagrams(DIAGRAM_DIR)
    body = build_body(figs)
    docx_path = OUT_DIR / "AgriTwin_Mini_Project_Report.docx"
    pdf_path = OUT_DIR / "AgriTwin_Mini_Project_Report.pdf"
    build_docx(docx_path, COVER, FRONT, body)
    build_pdf(pdf_path, COVER, FRONT, body)
    print(f"Wrote {docx_path}")
    print(f"Wrote {pdf_path}")
    print(f"Figures: {len(figs)}; body blocks: {len(body)}")


if __name__ == "__main__":
    main()
