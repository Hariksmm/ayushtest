"""
MRB AYUSH Pharmacist Exam Generator — Streamlit Edition
Converted from the original single-file HTML/JS "Spatial UI" app.

Run with:
    streamlit run ayush_exam_generator.py

Features carried over from the original app:
- Built-in MRB Question Vault (23 authentic high-yield MCQs) with an
  offline generator that shuffles / recombines / synthesizes variants
  to reach any requested question count.
- Optional Google Gemini Flash REST engine (bring your own API key) that
  generates fresh MCQs following the same MRB syllabus prompt used in
  the original app.
- Subject filter (Siddha / Ayurveda / Unani / Homeopathy / Allied),
  question count, difficulty style, and Study vs Practice-Exam modes.
- Deduplication ledger so repeated generations avoid repeating topics.
- Practice Exam scoring with the same verdict thresholds as the original.
- Markdown export and a print-style PDF export (questions first,
  official answer key & rationale grouped at the end).
"""

import json
import random
import time
from datetime import datetime

import requests
import streamlit as st

# ==============================================================================
# BUILT-IN MRB QUESTION VAULT  (ported verbatim from MRB_QUESTION_VAULT in the
# original HTML/JS file)
# ==============================================================================

MRB_QUESTION_VAULT = [
    # --- SIDDHA MEDICINE & GUNAPADAM (P1, P7, P13, P14) ---
    {
        "id": "sid-01", "subject": "Siddha", "moduleCode": "P13 (Gunapadam)",
        "topic": "Purification (Suddhi) of Lingam",
        "stem": "According to Gunapadam Thathuvam, which of the following media is specifically prescribed for the purification (Suddhi) of Lingam (Cinnabar / Red Mercuric Sulphide) before compounding Parpam or Chenduram?",
        "options": {
            "A": "Cow's Urine (Komuthiram) boiled for 3 hours",
            "B": "Lemon Juice (Elumicham Pazharasa) soaked or processed in sunlight",
            "C": "Ginger Juice (Inji Saaru) distilled in Valuka Yantra",
            "D": "Alkaline solution of Achyranthes aspera (Naayuruvi Uppu)",
        },
        "correct": "B",
        "rationale": "Lingam (Cinnabar, HgS) undergoes Suddhi primarily by boiling or soaking in lemon juice (Elumicham Pazharasa Suddhi) for 7 days or triturating till the toxic volatile sulphur contaminants are neutralized.",
        "syllabusRef": "Siddha Formulary of India Part I; Gunapadam Thathu Vaguppu",
    },
    {
        "id": "sid-02", "subject": "Siddha", "moduleCode": "P1 (Porul Nirnayam)",
        "topic": "7 Udal Kattukal (Body Constituents)",
        "stem": "In Siddha Pathophysiology, which Udal Kattu (Dhatu) is directly sustained and replenished by the nutrient fluid Saaram (Chyle) to form Chenneer (Blood)?",
        "options": {
            "A": "Oon (Muscle tissue)",
            "B": "Kozhuppu (Adipose tissue)",
            "C": "Chenneer (Blood tissue)",
            "D": "Moolai (Bone marrow)",
        },
        "correct": "C",
        "rationale": "The 7 Udal Kattukal form in successive progressive order: Saaram (Chyle) -> Chenneer (Blood) -> Oon (Muscle) -> Kozhuppu (Fat) -> Enbu (Bone) -> Moolai (Marrow) -> Sukkilam/Suronitham (Semen/Ovum). Saaram directly enriches Chenneer.",
        "syllabusRef": "Siddha Maruthuva Adippadai Thathuvangal",
    },
    {
        "id": "sid-03", "subject": "Siddha", "moduleCode": "P14 (Formulations)",
        "topic": "Thirikadugu Chooranam Ratio",
        "stem": "What is the classical proportion of ingredients in Thirikadugu Chooranam (Chukku, Milagu, and Thippili) according to the Siddha Formulary of India?",
        "options": {
            "A": "1 : 2 : 3 parts respectively",
            "B": "1 : 1 : 1 equal parts by weight",
            "C": "4 : 2 : 1 parts respectively",
            "D": "3 : 2 : 1 parts respectively",
        },
        "correct": "B",
        "rationale": "Thirikadugu Chooranam consists of dry ginger (Zingiber officinale / Chukku), black pepper (Piper nigrum / Milagu), and long pepper (Piper longum / Thippili) taken in equal parts (1:1:1 by weight), pulverized into fine powder.",
        "syllabusRef": "Siddha Pharmacopoeia & Formulary of India",
    },
    {
        "id": "sid-04", "subject": "Siddha", "moduleCode": "P7 (8 Diagnostic Methods)",
        "topic": "Envagai Thervu (Neikkuri Diagnostic Logic)",
        "stem": "In Siddha Neikkuri (Urine Oil-Drop examination), when a drop of sesame oil spreads immediately like a ring (Valayam) on the urine surface, which Uyir Thathu vitiation does it specifically diagnose?",
        "options": {
            "A": "Pure Vatha Kutram",
            "B": "Pure Pitha Kutram",
            "C": "Pure Kapha (Iyya) Kutram",
            "D": "Thontha Santhipatham (Incurable stage)",
        },
        "correct": "B",
        "rationale": "Therayar Neikkuri states: 'Aravupol ninradin akil vatham; aazhi pol paravin pitham; muthupol nirkil kaphame'. Spreading like a ring (Aazhi/Valayam) signifies Pitha Kutram.",
        "syllabusRef": "Therayar Neerkuri & Neikkuri Sastram",
    },
    {
        "id": "sid-05", "subject": "Siddha", "moduleCode": "P13 (Raw Drugs - Muligai)",
        "topic": "Sirukurinjan Botanical Identification",
        "stem": "Which of the following is the authentic botanical source of the renowned anti-diabetic Siddha herb 'Sirukurinjan' (Chakkarai Kolli)?",
        "options": {
            "A": "Andrographis paniculata",
            "B": "Gymnema sylvestre",
            "C": "Syzygium cumini",
            "D": "Cassia auriculata",
        },
        "correct": "B",
        "rationale": "Sirukurinjan is Gymnema sylvestre (family Apocynaceae/Asclepiadaceae). It contains gymnemic acids that abolish the taste sensation of sweetness and stimulate pancreatic beta cells.",
        "syllabusRef": "Gunapadam Mooligai Vaguppu",
    },
    # --- AYURVEDA MULA SIDDHANTHA & DRAVYAGUNA (P1, P7, P15, P16) ---
    {
        "id": "ayu-01", "subject": "Ayurveda", "moduleCode": "P15 (Dravyaguna)",
        "topic": "Triphala Constituents & Proportions",
        "stem": "According to Sharangadhara Samhita and the Ayurvedic Pharmacopoeia of India, what constitutes the classical formulation 'Triphala' and its standard ratio?",
        "options": {
            "A": "Haritaki, Bibhitaki, and Amalaki in equal parts (1:1:1)",
            "B": "Haritaki, Bibhitaki, and Amalaki in 1:2:4 ratio",
            "C": "Amalaki, Draksha, and Haritaki in equal parts",
            "D": "Shunthi, Maricha, and Pippali in equal parts",
        },
        "correct": "A",
        "rationale": "Standard Triphala Churna comprises the dried pericarp of Haritaki (Terminalia chebula), Bibhitaki (Terminalia bellirica), and Amalaki (Phyllanthus emblica) combined in equal parts (1:1:1 by weight).",
        "syllabusRef": "Ayurvedic Pharmacopoeia of India (API); Sharangadhara Samhita",
    },
    {
        "id": "ayu-02", "subject": "Ayurveda", "moduleCode": "P16 (Bhesajya Kalpana)",
        "topic": "Shelf Life (Saviryatha Kaala)",
        "stem": "According to classical Bhesajya Kalpana principles as codified in Ayurvedic regulatory texts, what is the traditional shelf-life (Saviryatha Kaala) of Choorna (fine herb powders) when stored in airtight containers?",
        "options": {
            "A": "Indefinite (increases with age like Asava)",
            "B": "2 months classically, extended to 1-2 years under modern Rules 161B",
            "C": "5 years without exception",
            "D": "16 years",
        },
        "correct": "B",
        "rationale": "According to Sharangadhara Samhita, Churna loses potency after 2 months. Under modern Rule 161B of Drugs & Cosmetics Rules, standard churna packaging allows a designated shelf life of 2 years.",
        "syllabusRef": "Sharangadhara Samhita Madhyama Khanda; D&C Rules Rule 161B",
    },
    {
        "id": "ayu-03", "subject": "Ayurveda", "moduleCode": "P1 (Mula Siddhantha)",
        "topic": "Agni Classification",
        "stem": "A patient presenting with irregular digestion—sometimes digesting heavy meals rapidly and at other times experiencing indigestion from light food—has which type of Agni governed by Vata dosha?",
        "options": {
            "A": "Samagni",
            "B": "Tikshnagni",
            "C": "Mandagni",
            "D": "Vishamagni",
        },
        "correct": "D",
        "rationale": "Vishamagni is variable/irregular digestive fire caused by the predominance of Vata dosha. Mandagni is caused by Kapha, Tikshnagni by Pitta, and Samagni reflects balanced Tridosha.",
        "syllabusRef": "Charaka Samhita Grahani Chikitsa Adhyaya",
    },
    {
        "id": "ayu-04", "subject": "Ayurveda", "moduleCode": "P16 (Rasa Sastra)",
        "topic": "Parada Shodhana (Mercury Purification)",
        "stem": "In the preliminary purification (Samanya Shodhana) of Parada (Hydrargyrum), which herb juice is thoroughly triturated with Mercury and lime (Churna) to remove Naga and Vanga doshas?",
        "options": {
            "A": "Kumari Swarasa (Aloe vera leaf juice)",
            "B": "Tulasi Swarasa (Ocimum sanctum)",
            "C": "Nimba Swarasa (Azadirachta indica)",
            "D": "Triphala Kwatha",
        },
        "correct": "A",
        "rationale": "Parada is triturated with Sudha (lime powder) and garlic (Lashuna), followed by extensive Mardana with Kumari Swarasa (Aloe vera pulp juice) to strip off volatile toxic metallurgical impurities.",
        "syllabusRef": "Rasa Ratna Samuccaya; Ayurvedic Formulary of India",
    },
    {
        "id": "ayu-05", "subject": "Ayurveda", "moduleCode": "P15 (Paripasha Groups)",
        "topic": "Dashamoola Composition",
        "stem": "Which of the following medicinal roots is classified under the 'Brihat Panchamoola' subgroup of Dashamoola?",
        "options": {
            "A": "Shalaparni (Desmodium gangeticum)",
            "B": "Prishniparni (Uraria picta)",
            "C": "Kantakari (Solanum surattense)",
            "D": "Bilva (Aegle marmelos)",
        },
        "correct": "D",
        "rationale": "Dashamoola consists of Brihat Panchamoola (Bilva, Agnimantha, Shyonaka, Patala, Gambhari) and Laghu Panchamoola (Brihati, Kantakari, Shalaparni, Prishniparni, Gokshura).",
        "syllabusRef": "Dravyaguna Vijnana; Charaka Samhita Sutrasthana Ch. 4",
    },
    # --- UNANI MEDICINE & ILMUL ADVIA (P1, P7, P11, P12) ---
    {
        "id": "una-01", "subject": "Unani", "moduleCode": "P1 (Umoor-E-Tabaiya)",
        "topic": "The 7 Natural Principles",
        "stem": "In Unani Tibb, how many essential fundamental physiological components constitute the Umoor-E-Tabaiya (The Basic Principles of Nature)?",
        "options": {
            "A": "4 Principles (Akhlat-e-Arba)",
            "B": "7 Principles (Arkan, Mizaj, Akhlath, Azai, Arwah, Quwa, Afaal)",
            "C": "9 Principles",
            "D": "12 Principles",
        },
        "correct": "B",
        "rationale": "Umoor-e-Tabaiya comprises exactly 7 physical constituents: Arkan (Elements), Mizaj (Temperament), Akhlat (Humours), Aaza (Organs), Arwah (Pneuma/Vital Spirits), Quwa (Faculties/Powers), and Afaal (Functions).",
        "syllabusRef": "Kulliyat-e-Umoor-e-Tabaiya; Avicenna's Canon of Medicine",
    },
    {
        "id": "una-02", "subject": "Unani", "moduleCode": "P12 (Murakkabat Formulations)",
        "topic": "Itrifal vs Majun Classification",
        "stem": "What is the key defining characteristic of an 'Itrifal' formulation in Unani Pharmacopoeia compared to other semi-solid Majun preparations?",
        "options": {
            "A": "It exclusively contains animal derivatives (Haiwani origin)",
            "B": "It invariably contains the triad of Post-e-Halela, Post-e-Balela, and Aamla (Triphala equivalent)",
            "C": "It is fermented like Sirka (vinegar) without honey base",
            "D": "It is prepared only as a liquid decoction",
        },
        "correct": "B",
        "rationale": "Itrifal is an Arabized form of 'Triphala'. All Itrifalat formulations (e.g., Itrifal Kishnizi, Itrifal Ustukhuddus) fundamentally contain Halela (Terminalia chebula), Balela (Terminalia bellirica), and Aamla (Emblica officinalis) in a honey/sugar base.",
        "syllabusRef": "National Formulary of Unani Medicine (NFUM) Part I",
    },
    {
        "id": "una-03", "subject": "Unani", "moduleCode": "P11 (Ilmul Advia & Mudabbir)",
        "topic": "Detoxification (Mudabbir) of Afiyoon",
        "stem": "Under Unani pharmaceutical regulations, which method is employed for the Mudabbir (detoxification/processing) of Afiyoon (Opium / Papaver somniferum latex)?",
        "options": {
            "A": "Boiling in milk (Shir-e-Khesht) followed by drying",
            "B": "Trituration with water of fresh coriander (Aab-e-Gishneez) until dissolved and dried",
            "C": "Incineration inside a sealed clay crucible (Bute-e-Gil)",
            "D": "Soaking in alcohol for 40 days",
        },
        "correct": "B",
        "rationale": "Afiyoon is detoxified (Tadbeer-e-Afiyoon) by triturating with fresh juice or water of coriander (Aab-e-Gishneez Tazah) or Araq-e-Gulab to temper its narcotizing and toxic dry-hot nature.",
        "syllabusRef": "Kitab-ul-Mudabbirat; Unani Pharmacopoeia of India",
    },
    {
        "id": "una-04", "subject": "Unani", "moduleCode": "P11 (Raw Drugs - Nabathi)",
        "topic": "Asgand Botanical & Mizaj",
        "stem": "What is the botanical identity and classical Unani Temperament (Mizaj) of the drug 'Asgand Nagori'?",
        "options": {
            "A": "Withania somnifera; Hot 2° and Dry 2° (Garm 2° Khushk 2°)",
            "B": "Asparagus racemosus; Cold 1° and Wet 2° (Barid 1° Ratab 2°)",
            "C": "Hyoscyamus niger; Cold 4° and Dry 4°",
            "D": "Glycyrrhiza glabra; Moderate (Motadil)",
        },
        "correct": "A",
        "rationale": "Asgand Nagori is Withania somnifera (Winter cherry). Its Mizaj is recognized as Hot in the 2nd degree and Dry in the 2nd degree (Garm o Khushk), serving as a potent Muqawwi-e-Bah (aphrodisiac) and Muwallid-e-Mani.",
        "syllabusRef": "Makhzan-ul-Advia; Unani Pharmacopoeia of India",
    },
    # --- HOMEOPATHY PHARMACY & MATERIA MEDICA (P1, P7, P9, P10) ---
    {
        "id": "hom-01", "subject": "Homeopathy", "moduleCode": "P9 (Organon of Medicine)",
        "topic": "Aphorisms on Homeopathic Pharmacy",
        "stem": "Which section of aphorisms in Dr. Samuel Hahnemann's Organon of Medicine (5th & 6th Editions) specifically governs the preparation, potentisation, and dispensing of medicines?",
        "options": {
            "A": "Aphorisms 1 to 20",
            "B": "Aphorisms 105 to 145",
            "C": "Aphorisms 264 to 285",
            "D": "Aphorisms 286 to 291",
        },
        "correct": "C",
        "rationale": "Aphorisms 264 to 285 deal specifically with Homeopathic Pharmacy: selection of genuine raw medicinal substances, preparation of mother tinctures, vehicles, and the science of potentisation (dynamisation).",
        "syllabusRef": "Organon of Medicine (6th Edition) by Dr. Samuel Hahnemann",
    },
    {
        "id": "hom-02", "subject": "Homeopathy", "moduleCode": "P10 (Potentisation Scales)",
        "topic": "Decimal vs Centesimal vs 50 Millesimal Scales",
        "stem": "Which homeopathic potentisation scale uses the ratio of 1 part of active medicinal substance to 99 parts of vehicle, denoted by the suffix 'C' or 'CH'?",
        "options": {
            "A": "Decimal Scale (introduced by Dr. Constantine Hering)",
            "B": "Centesimal Scale (introduced by Dr. Samuel Hahnemann)",
            "C": "50 Millesimal Scale (LM Scale)",
            "D": "Korsakovian Scale",
        },
        "correct": "B",
        "rationale": "The Centesimal Scale (1:100 ratio: 1 part medicine + 99 parts vehicle) was introduced by Dr. Samuel Hahnemann in the 5th edition of Organon. The Decimal scale (1:10 ratio) was later popularized by Dr. Constantine Hering.",
        "syllabusRef": "Homoeopathic Pharmacopoeia of India (HPI); A Text Book of Homeopathic Pharmacy",
    },
    {
        "id": "hom-03", "subject": "Homeopathy", "moduleCode": "P10 (Vehicles)",
        "topic": "Sugar of Milk (Saccharum Lactis)",
        "stem": "Which vehicle is utilized as the primary inert base for the preparation of solid triturations of insoluble minerals and elements in Homeopathic Pharmacy?",
        "options": {
            "A": "Saccharum Officinale (Cane sugar)",
            "B": "Saccharum Lactis (Sugar of milk / Lactose)",
            "C": "Microcrystalline Cellulose",
            "D": "Calcium phosphate",
        },
        "correct": "B",
        "rationale": "Sugar of Milk (Saccharum Lactis, C12H22O11·H2O), obtained from goat or cow milk whey, provides abrasive, non-hygroscopic, inert crystals ideal for mechanical attrition during Hahnemannian trituration.",
        "syllabusRef": "Homoeopathic Pharmacopoeia of India (HPI) Vol 1",
    },
    {
        "id": "hom-04", "subject": "Homeopathy", "moduleCode": "P9 (Drug Proving)",
        "topic": "Aphorisms 105-145",
        "stem": "According to Hahnemannian principles, on whom must 'Drug Proving' (Pathogenetic trial of medicinal substances) be carried out to ascertain true Materia Medica symptoms?",
        "options": {
            "A": "Laboratory mice and rabbits",
            "B": "Sick hospitalized patients suffering from chronic ailments",
            "C": "Healthy human provers of diverse ages and genders in moderate doses",
            "D": "Surgical convalescent individuals",
        },
        "correct": "C",
        "rationale": "Aphorisms 105–145 clearly emphasize that drug actions must be observed upon healthy human beings (both male and female), because animals cannot communicate subjective mental and emotional symptoms, and sick bodies confuse drug effects with disease symptoms.",
        "syllabusRef": "Organon of Medicine, Aphorism 108",
    },
    # --- ALLIED SCIENCES & LEGISLATION (P2–P6, P8) ---
    {
        "id": "all-01", "subject": "Allied", "moduleCode": "P8 (Drugs & Cosmetics Act 1940)",
        "topic": "Chapter IV-A Regulatory Scope",
        "stem": "Under the Drugs and Cosmetics Act 1940, which Chapter specifically contains the regulatory provisions for Ayurvedic, Siddha, and Unani (ASU) drugs (inserted via Act 13 of 1964)?",
        "options": {
            "A": "Chapter II",
            "B": "Chapter III",
            "C": "Chapter IV-A",
            "D": "Chapter V",
        },
        "correct": "C",
        "rationale": "Chapter IV-A (Sections 33B to 33O) of the Drugs & Cosmetics Act 1940 governs Ayurvedic, Siddha, and Unani drugs, covering manufacture, sale, labeling, and penalties.",
        "syllabusRef": "Drugs and Cosmetics Act 1940, Chapter IV-A",
    },
    {
        "id": "all-02", "subject": "Allied", "moduleCode": "P8 (D&C Rules 1945)",
        "topic": "Rule 158B (License for ASU Drugs)",
        "stem": "Under Rule 158B of the Drugs and Cosmetics Rules 1945, what is required for obtaining a manufacturing license for an ASU drug categorized as an 'Ayurvedic/Siddha/Unani Patent or Proprietary Medicine'?",
        "options": {
            "A": "No evidence required if ingredients are mentioned in Charaka Samhita",
            "B": "Proof of safety and effectiveness from published scientific research, safety studies, and reference to texts in First Schedule",
            "C": "Clinical trial Phase IV completion exclusively in foreign countries",
            "D": "A certificate from a local pharmacy shopkeeper",
        },
        "correct": "B",
        "rationale": "Rule 158B requires submitting proof of safety and effectiveness, based on published scientific literature or safety studies, with recipe ingredients derived strictly from authoritative classical books listed in the First Schedule.",
        "syllabusRef": "Drugs and Cosmetics Rules 1945, Rule 158B",
    },
    {
        "id": "all-03", "subject": "Allied", "moduleCode": "P8 (Schedules to D&C Rules)",
        "topic": "Schedule T (Good Manufacturing Practices)",
        "stem": "Which Schedule of the Drugs and Cosmetics Rules 1945 establishes mandatory 'Good Manufacturing Practices' (GMP) for premises, equipment, quality control, and personnel for Ayurvedic, Siddha, and Unani drugs?",
        "options": {
            "A": "Schedule M",
            "B": "Schedule T",
            "C": "Schedule Y",
            "D": "Schedule X",
        },
        "correct": "B",
        "rationale": "Schedule T prescribes GMP for Ayurvedic, Siddha, and Unani medicines. Schedule M applies to Allopathic drugs, Schedule Y to Clinical Trials, and Schedule X to Psychotropic/Narcotic substances.",
        "syllabusRef": "Drugs and Cosmetics Rules 1945, Schedule T",
    },
    {
        "id": "all-04", "subject": "Allied", "moduleCode": "P6 (Pharmacology & Physiology)",
        "topic": "First-Pass Hepatic Metabolism",
        "stem": "When an oral herbal decoction (Kashayam) is absorbed from the gastrointestinal tract into the portal circulation, which anatomical organ is primarily responsible for the 'first-pass metabolism' before the drug reaches systemic circulation?",
        "options": {
            "A": "Spleen",
            "B": "Liver",
            "C": "Kidneys",
            "D": "Pancreas",
        },
        "correct": "B",
        "rationale": "The portal venous system drains directly from the stomach and intestines into the Liver, where hepatic microsomal cytochrome P450 enzymes metabolize compounds prior to systemic distribution (First-Pass Hepatic Clearance).",
        "syllabusRef": "Essentials of Medical Pharmacology; Human Physiology",
    },
    {
        "id": "all-05", "subject": "Allied", "moduleCode": "P8 (D&C Rules - First Schedule)",
        "topic": "First Schedule Authoritative Books",
        "stem": "The First Schedule to the Drugs and Cosmetics Act 1940 lists authoritative classical texts. Which of the following is an official recognized Siddha classical text in this schedule?",
        "options": {
            "A": "Agathiyar Vaithiya Rathina Churukkam & Therayar Maha Karisal",
            "B": "Bhavaprakasha Nighantu",
            "C": "Al-Qanoon Fil Tibb",
            "D": "Materia Medica Pura",
        },
        "correct": "A",
        "rationale": "The First Schedule to the D&C Act lists official books: for Siddha it includes Therayar Yamagam, Agathiyar Vaithiya Rathina Churukkam, Gunapadam Mooligai, etc. Bhavaprakasha is Ayurvedic, and Al-Qanoon is Unani.",
        "syllabusRef": "Drugs and Cosmetics Act 1940, The First Schedule",
    },
]

# Extra topics used purely to synthesize variant items when a requested count
# exceeds the size of the filtered pool (ported from synthesizeVariantQuestion).
TOPIC_VARIANTS = [
    {
        "subject": "Siddha", "moduleCode": "P14 (Formulations)",
        "topic": "Parpam vs Chenduram Calcination",
        "stem": "Which organoleptic test verifies the completion of calcination (Puda Paagam) of a Siddha Parpam formulation to ensure absence of raw metallic particles?",
        "options": {
            "A": "Floating test on water (Varitharam) and enters finger crevices (Rekhapurnatvam)",
            "B": "Complete solubility in boiling alcohol",
            "C": "Turn black when exposed to sulfur fumes",
            "D": "Density equal to mercury",
        },
        "correct": "A",
        "rationale": "Varitharam (floating lightly on water) and Rekhapurnatvam (particle fineness entering the furrows of fingers) verify proper particle size down to nano-dimensions in classical Bhasma/Parpam.",
        "syllabusRef": "Siddha Formulary of India; Rasa Sastra Standard Tests",
    },
    {
        "subject": "Ayurveda", "moduleCode": "P15 (Dravyaguna)",
        "topic": "Rasa-Panchaka (Virya Concept)",
        "stem": "In Ayurvedic Pharmacology (Dravyaguna), which thermodynamic property (Virya) is attributed to Shunthi (Zingiber officinale)?",
        "options": {
            "A": "Sheeta Virya (Cold potency)",
            "B": "Ushna Virya (Hot potency)",
            "C": "Anushnasheeta (Temperate)",
            "D": "Snigdha Virya",
        },
        "correct": "B",
        "rationale": "Shunthi exhibits Katu Rasa, Madhura Vipaka, and Ushna Virya (Hot potency), balancing Vata and Kapha doshas.",
        "syllabusRef": "Dravyaguna Vijnana Part II",
    },
    {
        "subject": "Allied", "moduleCode": "P8 (D&C Act 1940)",
        "topic": "Schedule E(1) Poisonous Substances",
        "stem": "Which of the following substances is included under Schedule E(1) of the Drugs and Cosmetics Rules 1945 as a list of poisonous substances under the Ayurvedic/Siddha systems?",
        "options": {
            "A": "Vatsanabha (Aconitum ferox)",
            "B": "Haridra (Curcuma longa)",
            "C": "Yashtimadhu (Glycyrrhiza glabra)",
            "D": "Bhumyamalaki (Phyllanthus niruri)",
        },
        "correct": "A",
        "rationale": "Schedule E(1) contains toxic drugs requiring mandatory purification and cautionary labeling, including Vatsanabha (Aconitum), Jayapala (Croton tiglium), and Gunja (Abrus precatorius).",
        "syllabusRef": "Drugs and Cosmetics Rules 1945, Schedule E(1)",
    },
    {
        "subject": "Unani", "moduleCode": "P12 (Formulations)",
        "topic": "Khamira Preparation",
        "stem": "What distinguishes a 'Khamira' from a basic Majun in Unani Murakkabat pharmacy?",
        "options": {
            "A": "Addition of distilled alcohol base",
            "B": "Extensive whipping/beating of sugar/honey Qiwam until it becomes white and aerated",
            "C": "Prepared strictly without any plant drugs",
            "D": "Solidified into dry lozenges",
        },
        "correct": "B",
        "rationale": "Khamira is prepared by whipping the hot syrup (Qiwam) until air is entrained, transforming the reddish-brown syrup into a frothy, snow-white semi-solid cardiac tonic.",
        "syllabusRef": "National Formulary of Unani Medicine (NFUM)",
    },
    {
        "subject": "Homeopathy", "moduleCode": "P10 (Scale Calculations)",
        "topic": "50 Millesimal Scale Ratio",
        "stem": "In Dr. Hahnemann's 6th Edition of Organon, what is the exact drug strength ratio utilized in the LM (50 Millesimal) potency scale?",
        "options": {
            "A": "1 in 10",
            "B": "1 in 100",
            "C": "1 in 50,000",
            "D": "1 in 1,000",
        },
        "correct": "C",
        "rationale": "The 50 Millesimal potency (denoted as 0/1, 0/2 or LM 1, LM 2) operates on a proportion of 1 : 50,000, designed to produce gentle, rapid cures without violent homeopathic aggravations.",
        "syllabusRef": "Organon of Medicine (6th Edition), Aphorism 270",
    },
]

SUBJECT_CARDS = [
    {"key": "All", "label": "All Subjects", "code": "", "desc": "Composite mixed paper across every AYUSH stream", "icon": "🧭"},
    {"key": "Siddha", "label": "Siddha Gunapadam", "code": "P1, P7, P13, P14", "desc": "Porul Nirnayam, 7 Udal Kattukal, Suddhi, 18 Siddhars, Parpam & Chenduram", "icon": "🧪"},
    {"key": "Ayurveda", "label": "Ayurveda Mula", "code": "P1, P7, P15, P16", "desc": "Tridosha, Dravyaguna, Rasa Sastra, Bhesajya Kalpana, Dashamoola, Shodhana", "icon": "🌿"},
    {"key": "Unani", "label": "Unani Ilmul Advia", "code": "P1, P7, P11, P12", "desc": "Umoor-E-Tabaiya, Mudabbir procedures, Ashkalul Advia, Majun & Murakkabat", "icon": "⚗️"},
    {"key": "Homeopathy", "label": "Homeopathy Pharmacy", "code": "P1, P7, P9, P10", "desc": "Organon aphorisms 264-285, Trituration, Succussion, Decimal/Centesimal/LM", "icon": "💧"},
    {"key": "Allied", "label": "Allied & Legislation", "code": "P2–P6, P8", "desc": "D&C Act 1940 / Rules 1945, Chap 4A, Rule 158B, GMP Schedule T, Pharmacology", "icon": "⚖️"},
]

DIFFICULTY_OPTIONS = {
    "mrb_official": "MRB Official Entrance Standard",
    "high_yield_recall": "High-Yield Factual Recall (Botanical/Formulas)",
    "clinical_forensic": "Clinical Logic & Purification Suddhi",
    "legislation_intensive": "D&C Act & Forensic Pharmacy Heavy",
}

# ==============================================================================
# STATE
# ==============================================================================

def init_state():
    defaults = {
        "current_questions": [],
        "user_answers": {},
        "seen_stems": set(),
        "seen_topics": [],
        "view_mode": "study",           # study | quiz | markdown
        "answers_visible": True,
        "show_scorecard": False,
        "score": 0,
        "search_input": "",
        "toast_msg": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def dedup_add(q):
    stem_key = q["stem"].strip().lower()[:60]
    st.session_state.seen_stems.add(stem_key)
    if q.get("topic"):
        st.session_state.seen_topics.append(q["topic"].strip().lower())


def dedup_has(stem):
    return stem.strip().lower()[:60] in st.session_state.seen_stems


def dedup_reset():
    st.session_state.seen_stems = set()
    st.session_state.seen_topics = []


def dedup_excluded_list():
    return ", ".join(st.session_state.seen_topics[-25:])


def toast(msg):
    st.session_state.toast_msg = msg


# ==============================================================================
# BUILT-IN VAULT GENERATION  (ported from generateFromLocalVault / synthesizeVariantQuestion)
# ==============================================================================

def synthesize_variant_question(index):
    chosen = TOPIC_VARIANTS[index % len(TOPIC_VARIANTS)]
    q = dict(chosen)
    q["id"] = f"mrb-gen-{int(time.time() * 1000)}-{index}"
    return q


def generate_from_local_vault(subject_query, count):
    pool = list(MRB_QUESTION_VAULT)
    lower_query = (subject_query or "").lower()

    if lower_query not in ("all", "mockexam") and "mock" not in lower_query:
        filtered = [
            q for q in pool
            if lower_query in q["subject"].lower()
            or lower_query in q["topic"].lower()
            or lower_query in q["stem"].lower()
        ]
        if filtered:
            pool = filtered

    unseen = [q for q in pool if not dedup_has(q["stem"])]
    selected_pool = unseen if len(unseen) >= count else pool
    selected_pool = list(selected_pool)
    random.shuffle(selected_pool)

    results = []
    for i in range(count):
        if not selected_pool:
            break
        base = selected_pool[i % len(selected_pool)]
        if i < len(selected_pool):
            q = dict(base)
            q["id"] = f"mrb-{int(time.time() * 1000)}-{i}"
            results.append(q)
        else:
            results.append(synthesize_variant_question(i + 1))
    return results


# ==============================================================================
# GEMINI REST ENGINE  (ported from fetchFromGeminiRest)
# ==============================================================================

def build_system_prompt(subject, count, difficulty, excluded_topics):
    return f"""You are an expert Medical Services Recruitment Board (MRB) official question setter specializing in the AYUSH Pharmacist Examination.
Generate exactly {count} authentic, precise Multiple-Choice Questions (MCQs) for Tamil Nadu MRB AYUSH Pharmacist standard.
Subjects: Siddha (P1,P7,P13,P14), Ayurveda (P1,P7,P15,P16), Unani (P1,P7,P11,P12), Homeopathy (P1,P7,P9,P10), Allied Sciences & Drugs & Cosmetics Act 1940/1945 (Chapter 4A, Rules 158B, 161, Schedule T).
Specific Request: {subject}.
Difficulty Style: {difficulty}.
DEDUPLICATION RULE: NEVER repeat previously generated concepts. EXCLUDE: [{excluded_topics or 'None yet'}].
EVERY MCQ MUST HAVE:
- Exactly 4 options (A, B, C, D) with ONLY 1 unambiguously correct option.
- Detailed pharmacological/clinical rationale with classical book or statutory rule citation.

RETURN STRICTLY A VALID JSON ARRAY OF OBJECTS with this exact structure:
[
  {{
    "id": "gem-1",
    "subject": "Siddha" (or Ayurveda, Unani, Homeopathy, Allied),
    "moduleCode": "P13 (Gunapadam)",
    "topic": "Specific Topic Name",
    "stem": "Question text here...",
    "options": {{
      "A": "Option text",
      "B": "Option text",
      "C": "Option text",
      "D": "Option text"
    }},
    "correct": "A",
    "rationale": "In-depth rationale citing formulary or act...",
    "syllabusRef": "Reference text"
  }}
]
Do NOT wrap in extra chat or explanations, only valid JSON."""


def fetch_from_gemini_rest(subject, count, difficulty, api_key, model):
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    system_prompt = build_system_prompt(subject, count, difficulty, dedup_excluded_list())

    payload = {
        "contents": [{"parts": [{"text": system_prompt}]}],
        "generationConfig": {"temperature": 0.25, "topK": 40, "topP": 0.95},
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=60)
    except requests.exceptions.Timeout:
        raise RuntimeError("Gemini request timed out after 60 seconds. Check your connection and try again.")
    except requests.exceptions.RequestException:
        raise RuntimeError("Could not connect to Gemini. Check your internet connection and API key restrictions.")

    if not response.ok:
        try:
            error_body = response.json()
            error_message = error_body.get("error", {}).get("message", f"HTTP {response.status_code}")
        except Exception:
            error_message = f"HTTP {response.status_code}"
        raise RuntimeError(f"Gemini API error: {error_message}")

    data = response.json()
    try:
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError("Empty response from Gemini API")

    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

    return json.loads(cleaned.strip())


# ==============================================================================
# COMMAND PARSER  (ported from parseAndRunCommand)
# ==============================================================================

def parse_and_run_command(raw_input, subject_filter, question_count):
    text = (raw_input or "").strip()

    if text.startswith("/reset_history"):
        dedup_reset()
        toast("Deduplication tracking history cleared.")
        return None, None

    if text.startswith("/export_pdf"):
        return "EXPORT_PDF", None

    if text.startswith("/mock_exam"):
        parts = text.split(" ")
        count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else (question_count or 15)
        return "MockExam", count

    if text.startswith("/generate"):
        parts = text.split(" ")
        subject = parts[1] if len(parts) > 1 else "All"
        count = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else (question_count or 10)
        return subject, count

    if text:
        return text, question_count

    return subject_filter, question_count


# ==============================================================================
# MARKDOWN / PDF EXPORT
# ==============================================================================

def render_markdown_view(questions):
    md = "# MEDICAL SERVICES RECRUITMENT BOARD (MRB) - AYUSH PHARMACIST EXAM\n"
    md += f"**Total Items:** {len(questions)} | **Standard:** TN MRB Official\n\n---\n\n"
    md += "## SECTION I: MULTIPLE CHOICE QUESTIONS\n\n"
    for i, q in enumerate(questions):
        md += f"### Q{i + 1}. [{q['subject']} - {q.get('moduleCode', '')}] {q['stem']}\n"
        for opt in "ABCD":
            md += f"- **({opt})** {q['options'].get(opt, '')}\n"
        md += "\n"
    md += "---\n\n## SECTION II: OFFICIAL ANSWER KEYS & CLINICAL RATIONALE\n\n"
    md += "| Q.No | Subject | Correct Option | Reference & Pharmacological Rationale |\n"
    md += "| :---: | :---: | :---: | :--- |\n"
    for i, q in enumerate(questions):
        rationale = q["rationale"].replace("|", "-")
        ref = q.get("syllabusRef", "MRB Syllabus")
        md += f"| **{i + 1}** | {q['subject']} | **({q['correct']})** | {rationale} *[Ref: {ref}]* |\n"
    return md


def build_pdf(questions, title="MRB AYUSH Practice Set"):
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    def safe(text):
        return (text or "").encode("latin-1", "replace").decode("latin-1")

    # --- Section I: Questions ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 8, safe("Medical Services Recruitment Board (MRB) - Tamil Nadu"), ln=True, align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 7, safe("Competitive Examination for the Post of Pharmacist (AYUSH)"), ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, safe(f"Total Questions: {len(questions)}   |   Time Allowed: 120 Minutes   |   Max Marks: 100"), ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "SECTION I: MULTIPLE CHOICE QUESTIONS", ln=True)
    pdf.set_font("Helvetica", "", 10)

    for i, q in enumerate(questions):
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(0, 6, safe(f"{i + 1}. [{q['subject']} - {q.get('moduleCode', '')}] {q['stem']}"))
        pdf.set_font("Helvetica", "", 10)
        for opt in "ABCD":
            pdf.multi_cell(0, 6, safe(f"   ({opt}) {q['options'].get(opt, '')}"))
        pdf.ln(2)

    # --- Section II: Answer key & rationale, on a fresh page ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "OFFICIAL ANSWER KEY & PHARMACOLOGICAL RATIONALE", ln=True, align="C")
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 5, safe(
        "Standards: Tamil Nadu MRB AYUSH Pharmacist Board. Formulations cited from Pharmacopoeial Standards "
        "(Siddha Formulary of India, Ayurvedic Pharmacopoeia of India, National Formulary of Unani Medicine, "
        "Homoeopathic Pharmacopoeia of India, Drugs & Cosmetics Act 1940)."
    ))
    pdf.ln(2)

    for i, q in enumerate(questions):
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(0, 6, safe(f"Q{i + 1} [{q['subject']}] — Correct Option: ({q['correct']})"))
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, safe(q["rationale"]))
        pdf.set_font("Helvetica", "I", 8)
        pdf.multi_cell(0, 5, safe(f"Reference: {q.get('syllabusRef', 'AYUSH Pharmacopoeia')}"))
        pdf.ln(3)

    return bytes(pdf.output(dest="S"))


# ==============================================================================
# STREAMLIT UI
# ==============================================================================

st.set_page_config(page_title="MRB AYUSH Pharmacist Exam Generator", page_icon="⚛️", layout="wide")
init_state()

# ---- Dark "spatial" theme styling (approximating the original CSS palette) ----
st.markdown(
    """
    <style>
      .stApp {
        background: radial-gradient(circle at 50% 15%, #0d1527 0%, #05070f 75%);
        color: #f8fafc;
      }
      section[data-testid="stSidebar"] {
        background: rgba(18, 24, 38, 0.9);
      }
      .glow-title {
        font-size: 2rem; font-weight: 800;
        background: linear-gradient(135deg, #00f0ff, #a855f7);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      }
      .subject-card {
        background: rgba(18, 24, 38, 0.65);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px; padding: 14px 16px; margin-bottom: 8px;
      }
      .badge {
        display:inline-block; font-family: monospace; font-size: 0.72rem;
        color:#94a3b8; background: rgba(255,255,255,0.06);
        padding: 3px 8px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);
      }
      .q-card {
        background: rgba(18, 24, 38, 0.55); border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px; padding: 18px 20px; margin-bottom: 16px;
      }
      .correct-pill { color:#00ff88; font-weight:700; }
      .wrong-pill { color:#ff0055; font-weight:700; }
      .rationale-box {
        margin-top: 12px; padding: 14px 18px; background: rgba(10,18,30,0.9);
        border-left: 4px solid #00ff88; border-radius: 0 10px 10px 0; color:#cbd5e1;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

if st.session_state.toast_msg:
    st.toast(st.session_state.toast_msg)
    st.session_state.toast_msg = None

st.markdown('<div class="glow-title">⚛️ MRB AYUSH Question Generator</div>', unsafe_allow_html=True)
st.caption(
    "Official Syllabus Standards: Siddha • Ayurveda • Unani • Homeopathy • Allied — "
    "high-yield MCQs with clinical rationales and D&C Act 1940/1945 provisions."
)

ledger_count = len(st.session_state.seen_stems)
st.markdown(f'<span class="badge">🧬 {ledger_count} Unique Concepts Logged</span>', unsafe_allow_html=True)
st.write("")

# ---------------- Sidebar: engine + parameters ----------------
with st.sidebar:
    st.header("⚙️ Configuration")

    engine = st.selectbox(
        "Engine",
        options=["built_in_mrb", "gemini_api"],
        format_func=lambda k: {
            "built_in_mrb": "Built-in MRB Vault (offline, no key required)",
            "gemini_api": "Google Gemini Flash REST (API key required)",
        }[k],
    )

    api_key = ""
    model_name = "gemini-2.5-flash"
    if engine == "gemini_api":
        with st.expander("🔑 Gemini API Key", expanded=True):
            api_key = st.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")
            model_name = st.text_input("Model version", value="gemini-2.5-flash")
            st.caption("Your key is only kept in this browser session's memory — it is never written to disk.")

    subject_filter = st.selectbox(
        "Subject",
        options=[c["key"] for c in SUBJECT_CARDS],
        format_func=lambda k: next(c["label"] for c in SUBJECT_CARDS if c["key"] == k),
    )

    question_count = st.select_slider("Question Count", options=[5, 10, 20, 50], value=10)

    difficulty = st.selectbox(
        "Difficulty",
        options=list(DIFFICULTY_OPTIONS.keys()),
        format_func=lambda k: DIFFICULTY_OPTIONS[k],
    )

    answer_mode = st.radio(
        "Answers",
        options=["study", "quiz"],
        format_func=lambda k: "Generate With Answers & Rationale" if k == "study" else "Generate Practice Exam (Hide Answers)",
    )

    if st.button("🔄 Reset Deduplication History", use_container_width=True):
        dedup_reset()
        st.rerun()

# ---------------- Subject dock (cards, click-to-select info only) ----------------
cols = st.columns(len(SUBJECT_CARDS))
for col, card in zip(cols, SUBJECT_CARDS):
    with col:
        active = " (selected)" if card["key"] == subject_filter else ""
        st.markdown(
            f"""<div class="subject-card">
                <div style="font-size:1.4rem;">{card['icon']}</div>
                <div style="font-weight:700; margin-top:4px;">{card['label']}</div>
                <div class="badge" style="margin-top:6px;">{card['code']}</div>
                <div style="font-size:0.78rem; color:#94a3b8; margin-top:6px;">{card['desc']}</div>
            </div>""",
            unsafe_allow_html=True,
        )

# ---------------- Search / command bar ----------------
search_col, btn_col = st.columns([5, 1])
with search_col:
    search_input = st.text_input(
        "Search or command",
        value=st.session_state.search_input,
        placeholder="Search topic or enter a command (e.g. /mock_exam 20, Gunapadam, D&C Act, Suddhi)...",
        label_visibility="collapsed",
    )
with btn_col:
    generate_clicked = st.button("⚡ Generate", use_container_width=True)

chip_cols = st.columns(4)
chip_commands = [
    ("🎓 /mock_exam 15", "/mock_exam 15"),
    ("🧪 /generate Siddha 10", "/generate Siddha 10"),
    ("🌿 /generate Ayurveda 10", "/generate Ayurveda 10"),
    ("⚗️ /generate Unani 10", "/generate Unani 10"),
    ("💧 /generate Homeopathy 10", "/generate Homeopathy 10"),
    ("⚖️ /generate Allied 10", "/generate Allied 10"),
    ("📄 /export_pdf", "/export_pdf"),
    ("↩️ /reset_history", "/reset_history"),
]
chip_clicked = None
for i, (label, cmd) in enumerate(chip_commands):
    with chip_cols[i % 4]:
        if st.button(label, key=f"chip_{i}", use_container_width=True):
            chip_clicked = cmd

# ---------------- Run generation ----------------
def run_generation(target_subject, target_count):
    st.session_state.user_answers = {}
    st.session_state.show_scorecard = False
    st.session_state.view_mode = answer_mode

    if engine == "gemini_api":
        if not api_key or len(api_key.strip()) <= 5:
            toast("Enter a Gemini API key before generating questions.")
            return
        try:
            with st.spinner(f"Querying Google Gemini Flash REST API for {target_subject}..."):
                questions = fetch_from_gemini_rest(
                    target_subject, target_count, DIFFICULTY_OPTIONS[difficulty], api_key.strip(), model_name.strip() or "gemini-2.5-flash"
                )
        except Exception as e:
            toast(f"Generation failed: {e}")
            return
    else:
        with st.spinner(f"Assembling {target_count} MCQs for {target_subject} from the MRB Vault..."):
            questions = generate_from_local_vault(target_subject, target_count)

    for q in questions:
        dedup_add(q)

    st.session_state.current_questions = questions
    toast(f"Generated {len(questions)} questions for {target_subject}.")


trigger_cmd, trigger_count = (None, None)
if generate_clicked:
    trigger_cmd, trigger_count = parse_and_run_command(search_input, subject_filter, question_count)
elif chip_clicked:
    trigger_cmd, trigger_count = parse_and_run_command(chip_clicked, subject_filter, question_count)

if trigger_cmd == "EXPORT_PDF":
    if not st.session_state.current_questions:
        toast("Generate questions first before exporting to PDF.")
    else:
        st.session_state["_do_pdf_export"] = True
elif trigger_cmd:
    run_generation(trigger_cmd, trigger_count or question_count)
    st.rerun()

# ---------------- Output window ----------------
questions = st.session_state.current_questions

if questions:
    st.divider()
    header_col1, header_col2 = st.columns([3, 2])
    with header_col1:
        st.subheader(f"📋 MRB Exam Paper — {len(questions)} Items")
    with header_col2:
        view_choice = st.radio(
            "View",
            options=["study", "quiz", "markdown"],
            index=["study", "quiz", "markdown"].index(st.session_state.view_mode),
            format_func=lambda k: {"study": "With Answers & Rationale", "quiz": "Practice Exam", "markdown": "Markdown / Code"}[k],
            horizontal=True,
            label_visibility="collapsed",
        )
        st.session_state.view_mode = view_choice

    export_col1, export_col2, _ = st.columns([1, 1, 3])
    with export_col1:
        md_text = render_markdown_view(questions)
        st.download_button("⬇️ Download Markdown", md_text, file_name="mrb_ayush_practice_set.md", mime="text/markdown", use_container_width=True)
    with export_col2:
        try:
            pdf_bytes = build_pdf(questions)
            st.download_button("⬇️ Download PDF", pdf_bytes, file_name="mrb_ayush_practice_set.pdf", mime="application/pdf", use_container_width=True)
        except ImportError:
            st.caption("Install `fpdf2` (pip install fpdf2) to enable PDF export.")

    if st.session_state.view_mode == "markdown":
        st.code(render_markdown_view(questions), language="markdown")

    else:
        is_study = st.session_state.view_mode == "study"

        for idx, q in enumerate(questions):
            with st.container():
                st.markdown('<div class="q-card">', unsafe_allow_html=True)
                st.markdown(
                    f'<span class="badge">{q["subject"]} • {q.get("moduleCode", "")}</span> '
                    f'<span style="float:right; color:#94a3b8; font-size:0.8rem;">Question {idx + 1} of {len(questions)}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{idx + 1}. {q['stem']}**")

                opt_keys = ["A", "B", "C", "D"]
                labels = [f"({k}) {q['options'].get(k, '')}" for k in opt_keys]

                if is_study:
                    for k, label in zip(opt_keys, labels):
                        if k == q["correct"]:
                            st.markdown(f"✅ **{label}**  <span class='correct-pill'>Correct Option</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(label)
                    st.markdown(
                        f"""<div class="rationale-box">
                            <b>Official Answer: Option ({q['correct']})</b><br>{q['rationale']}
                            <div class="badge" style="margin-top:8px;">Reference: {q.get('syllabusRef', '')}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                else:
                    prior = st.session_state.user_answers.get(idx)
                    default_index = opt_keys.index(prior) if prior in opt_keys else None
                    choice = st.radio(
                        f"q_{idx}", options=opt_keys, format_func=lambda k, labels=labels, opt_keys=opt_keys: labels[opt_keys.index(k)],
                        index=default_index, key=f"radio_{idx}", label_visibility="collapsed",
                    )
                    if choice:
                        st.session_state.user_answers[idx] = choice

                    if st.session_state.show_scorecard:
                        user_choice = st.session_state.user_answers.get(idx)
                        if user_choice == q["correct"]:
                            st.markdown(f"<span class='correct-pill'>✔ Correct — Option ({q['correct']})</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(
                                f"<span class='wrong-pill'>✘ Your answer: ({user_choice or '—'})</span> &nbsp; "
                                f"<span class='correct-pill'>Correct: ({q['correct']})</span>",
                                unsafe_allow_html=True,
                            )
                        st.markdown(
                            f"""<div class="rationale-box">{q['rationale']}
                                <div class="badge" style="margin-top:8px;">Reference: {q.get('syllabusRef', '')}</div>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.view_mode == "quiz":
            st.divider()
            answered = len(st.session_state.user_answers)
            footer_col1, footer_col2, footer_col3 = st.columns([2, 1, 1])
            with footer_col1:
                st.write(f"Questions Answered: **{answered}** of {len(questions)}")
            with footer_col2:
                if st.button("↩️ Reset Answers", use_container_width=True):
                    st.session_state.user_answers = {}
                    st.session_state.show_scorecard = False
                    st.rerun()
            with footer_col3:
                if st.button("✅ Submit Exam", type="primary", use_container_width=True):
                    score = sum(
                        1 for idx, q in enumerate(questions)
                        if st.session_state.user_answers.get(idx) == q["correct"]
                    )
                    st.session_state.score = score
                    st.session_state.show_scorecard = True
                    st.rerun()

            if st.session_state.show_scorecard:
                score = st.session_state.score
                total = len(questions)
                pct = round(score / total * 100) if total else 0
                if pct >= 70:
                    verdict, color, msg = f"Outstanding Merit! ({pct}%)", "#00ff88", "Performance mirrors high-rank MRB selection cutoff. Review explanations above."
                elif pct >= 50:
                    verdict, color, msg = f"Qualified Score ({pct}%)", "#00f0ff", "Solid understanding of AYUSH core modules. Strengthen D&C Act & Suddhi procedures."
                else:
                    verdict, color, msg = f"Needs Revision ({pct}%)", "#ffb703", "Focus study on classical text references, Gunapadam, and Rules 158B & 161."

                st.markdown(
                    f"""<div style="text-align:center; padding: 24px; border-radius:16px;
                        background: radial-gradient(circle at 50% 30%, rgba(0,240,255,0.15) 0%, transparent 60%);">
                        <div style="font-size:2.2rem; font-weight:800; font-family:monospace;">{score} / {total}</div>
                        <div style="font-size:1.3rem; font-weight:700; color:{color}; margin-top:8px;">{verdict}</div>
                        <div style="color:#94a3b8; margin-top:6px;">{msg}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
else:
    st.info("Pick a subject, set your question count, then click **Generate** (or use a quick command chip) to build your first practice set.")

st.divider()
st.caption(f"MRB AYUSH Pharmacist Exam Generator · Streamlit Edition · {datetime.now():%Y}")
