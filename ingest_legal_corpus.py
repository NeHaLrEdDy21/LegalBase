"""
Legal Corpus Ingestion Script
Ingests Indian Constitution, IPC, Contract Act, and other legal texts into FAISS + Supabase

Run from D:/mini project/ with:
  "C:/Users/Nehal Reddy/AppData/Local/Programs/Python/Python312/python.exe" ingest_legal_corpus.py
"""

import sys
import os
import uuid
import json

# ── path setup ──────────────────────────────────────────────────────────────
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(THIS_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)

# ── load .env manually ──────────────────────────────────────────────────────
def load_env(path):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

load_env(os.path.join(BACKEND_DIR, ".env"))
load_env(os.path.join(THIS_DIR, ".env"))

# ── legal corpus ─────────────────────────────────────────────────────────────
LEGAL_CORPUS = [

    # ══════════════════════════════════════════════════════════════════════
    # INDIAN CONSTITUTION
    # ══════════════════════════════════════════════════════════════════════
    {
        "title": "Constitution of India – Preamble",
        "category": "CONSTITUTIONAL",
        "jurisdiction": "India",
        "text": (
            "WE, THE PEOPLE OF INDIA, having solemnly resolved to constitute India into a "
            "SOVEREIGN SOCIALIST SECULAR DEMOCRATIC REPUBLIC and to secure to all its citizens: "
            "JUSTICE, social, economic and political; LIBERTY of thought, expression, belief, faith "
            "and worship; EQUALITY of status and of opportunity; and to promote among them all "
            "FRATERNITY assuring the dignity of the individual and the unity and integrity of the "
            "Nation; IN OUR CONSTITUENT ASSEMBLY this twenty-sixth day of November, 1949, do "
            "HEREBY ADOPT, ENACT AND GIVE TO OURSELVES THIS CONSTITUTION."
        ),
    },
    {
        "title": "Constitution of India – Fundamental Rights (Articles 12–35)",
        "category": "CONSTITUTIONAL",
        "jurisdiction": "India",
        "text": (
            "Article 12 – Definition of State includes the Government and Parliament of India, "
            "Government and Legislature of each State, and all local or other authorities. "
            "Article 13 – Laws inconsistent with fundamental rights shall be void. "
            "Article 14 – Equality before law: The State shall not deny equality before the law "
            "or equal protection of the laws within India. "
            "Article 15 – Prohibition of discrimination on grounds of religion, race, caste, sex "
            "or place of birth. "
            "Article 16 – Equality of opportunity in matters of public employment. "
            "Article 17 – Abolition of Untouchability. "
            "Article 19 – Protection of six freedoms: speech and expression; assemble peaceably "
            "without arms; form associations; move freely; reside and settle; practise any "
            "profession or trade. "
            "Article 20 – Protection against conviction for offences: no ex post facto law; "
            "no double jeopardy; no self-incrimination. "
            "Article 21 – Protection of life and personal liberty: No person shall be deprived "
            "of his life or personal liberty except according to procedure established by law. "
            "Article 21A – Right to free and compulsory education for children aged 6-14 years. "
            "Article 22 – Protection against arrest and detention: right to be informed of grounds, "
            "right to consult a lawyer, production before magistrate within 24 hours. "
            "Article 23 – Prohibition of traffic in human beings and forced labour. "
            "Article 24 – No child below 14 years shall be employed in any factory, mine or "
            "hazardous employment. "
            "Article 25 – Freedom of conscience and free profession, practice and propagation "
            "of religion. "
            "Article 32 – Right to constitutional remedies: Supreme Court may issue writs of "
            "habeas corpus, mandamus, prohibition, quo warranto, and certiorari."
        ),
    },
    {
        "title": "Constitution of India – Directive Principles (Articles 36–51)",
        "category": "CONSTITUTIONAL",
        "jurisdiction": "India",
        "text": (
            "Article 38 – State to secure a social order for welfare of the people. "
            "Article 39 – Equal pay for equal work; equitable distribution of material resources; "
            "no concentration of wealth. "
            "Article 39A – Equal justice and free legal aid to the poor. "
            "Article 40 – Organisation of village panchayats. "
            "Article 41 – Right to work, education and public assistance. "
            "Article 44 – Uniform Civil Code for citizens. "
            "Article 45 – Early childhood care and education for children below 6 years. "
            "Article 46 – Promotion of educational and economic interests of SC, ST and weaker "
            "sections. "
            "Article 47 – Duty to raise nutrition level and standard of living. "
            "Article 50 – Separation of judiciary from executive. "
            "Article 51 – Promotion of international peace and security."
        ),
    },
    {
        "title": "Constitution of India – Fundamental Duties (Article 51A)",
        "category": "CONSTITUTIONAL",
        "jurisdiction": "India",
        "text": (
            "Article 51A – Fundamental Duties of every citizen: abide by the Constitution; "
            "cherish noble ideals of freedom struggle; uphold sovereignty and integrity of India; "
            "defend the country when called upon; promote harmony and brotherhood among all people; "
            "value and preserve rich heritage of composite culture; protect and improve the natural "
            "environment; develop scientific temper and spirit of inquiry; safeguard public property "
            "and abjure violence; strive towards excellence; provide opportunities for education "
            "to children aged 6-14 years."
        ),
    },
    {
        "title": "Constitution of India – The Union: President, Parliament, Supreme Court (Articles 52–151)",
        "category": "CONSTITUTIONAL",
        "jurisdiction": "India",
        "text": (
            "Article 52 – There shall be a President of India. "
            "Article 53 – Executive power of the Union vested in the President. "
            "Article 61 – Procedure for impeachment of the President. "
            "Article 72 – Power of President to grant pardons, reprieves, respites or remissions. "
            "Article 74 – Council of Ministers to aid and advise the President. "
            "Article 76 – Attorney-General for India: appears on behalf of Union of India in "
            "Supreme Court. "
            "Article 79 – Parliament consists of President, Rajya Sabha and Lok Sabha. "
            "Article 100 – Voting in Houses. "
            "Article 108 – Joint sitting of both Houses to resolve deadlock. "
            "Article 110 – Definition of Money Bills. "
            "Article 112 – Annual financial statement (Union Budget). "
            "Article 124 – Establishment and constitution of Supreme Court. "
            "Article 129 – Supreme Court to be a court of record. "
            "Article 131 – Original jurisdiction: disputes between States, or State and Union. "
            "Article 132 – Appellate jurisdiction in constitutional cases. "
            "Article 136 – Special leave to appeal by Supreme Court (SLP). "
            "Article 141 – Law declared by Supreme Court to be binding on all courts. "
            "Article 143 – Advisory jurisdiction: President may consult Supreme Court. "
            "Article 148 – Comptroller and Auditor-General of India."
        ),
    },
    {
        "title": "Constitution of India – Emergency Provisions (Articles 352–360)",
        "category": "CONSTITUTIONAL",
        "jurisdiction": "India",
        "text": (
            "Article 352 – Proclamation of National Emergency on grounds of war, external "
            "aggression, or armed rebellion. During National Emergency: Art. 19 rights "
            "automatically suspended; Art. 20 and 21 cannot be suspended. "
            "Article 356 – President's Rule in States when constitutional machinery fails. "
            "Article 360 – Financial Emergency when financial stability of India is threatened. "
            "Article 358 – Suspension of provisions of Article 19 during National Emergency. "
            "Article 359 – Suspension of enforcement of rights under Part III."
        ),
    },
    {
        "title": "Constitution of India – Amendment Procedure and Basic Structure Doctrine (Article 368)",
        "category": "CONSTITUTIONAL",
        "jurisdiction": "India",
        "text": (
            "Article 368 – Power of Parliament to amend the Constitution. "
            "Requires special majority: two-thirds of members present and voting plus majority "
            "of total membership. Certain provisions also require ratification by at least "
            "half of State Legislatures. "
            "Basic Structure Doctrine – Kesavananda Bharati v. State of Kerala (1973): Parliament "
            "cannot amend the Constitution so as to destroy its basic structure. "
            "Basic structure includes: supremacy of the Constitution; republican and democratic "
            "government; secular character; separation of powers; federal character; judicial "
            "review; free and fair elections; rule of law; unity and integrity of India."
        ),
    },
    {
        "title": "Constitution of India – Federalism, States, and Legislative Relations (Articles 245–263)",
        "category": "CONSTITUTIONAL",
        "jurisdiction": "India",
        "text": (
            "Article 245 – Extent of laws made by Parliament and by Legislatures of States. "
            "Article 246 – Subject-matter of laws made by Parliament and State Legislatures. "
            "Seventh Schedule: Union List (List I, 97 subjects — Parliament has exclusive power), "
            "State List (List II, 66 subjects — States have exclusive power), "
            "Concurrent List (List III, 47 subjects — both Parliament and States can legislate). "
            "In case of conflict, Union law prevails over State law on Concurrent List. "
            "Article 248 – Residuary powers of legislation vest in Parliament. "
            "Article 249 – Parliament may legislate on State List matters in national interest. "
            "Article 256 – Obligation of States and the Union. "
            "Article 257 – Control of the Union over States in certain cases. "
            "Article 263 – Inter-State Council for coordination."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # INDIAN PENAL CODE / BNS 2023
    # ══════════════════════════════════════════════════════════════════════
    {
        "title": "Indian Penal Code 1860 – General Principles (Sections 1–75)",
        "category": "CRIMINAL",
        "jurisdiction": "India",
        "text": (
            "Section 2 – Punishment of offences committed within India. "
            "Section 11 – 'Person' includes any Company or Association or body of persons. "
            "Section 23 – Wrongful gain: gain by unlawful means of property one is not entitled to. "
            "Section 24 – Dishonestly: doing anything with intention of causing wrongful gain or loss. "
            "Section 34 – Acts done by several persons in furtherance of common intention: each "
            "is liable as if done by him alone. "
            "Section 76–106 – General Exceptions: act done by a person bound by law; act of judge; "
            "accident without criminal intent; act done in good faith; consent; communication by "
            "doctor in good faith; duress; trifling acts. "
            "Section 96 – Acts in private defence are not offences. "
            "Section 97 – Right of private defence of body and property. "
            "Section 100 – When right of private defence of body extends to causing death: "
            "assault with reasonable apprehension of death, grievous hurt, rape, kidnapping, "
            "wrongful confinement."
        ),
    },
    {
        "title": "Indian Penal Code 1860 – Offences Against Human Body (Sections 299–377)",
        "category": "CRIMINAL",
        "jurisdiction": "India",
        "text": (
            "Section 299 – Culpable homicide: causing death by act with intention of causing death "
            "or knowledge that death is likely to result. "
            "Section 300 – Murder: culpable homicide amounts to murder if done with intention of "
            "causing death, or bodily injury likely to cause death. "
            "Section 302 – Punishment for murder: Death or imprisonment for life and fine. "
            "Section 304 – Culpable homicide not amounting to murder: imprisonment up to 10 years "
            "or life imprisonment depending on intent. "
            "Section 304A – Causing death by negligence (rash/negligent act): imprisonment up to "
            "2 years or fine or both. "
            "Section 307 – Attempt to murder: imprisonment up to 10 years and fine. "
            "Section 319 – Hurt: causing bodily pain, disease or infirmity. "
            "Section 320 – Grievous hurt: includes permanent deprivation of sight/hearing, "
            "loss of member/joint, disfiguration, fracture, endangering life. "
            "Section 323 – Punishment for voluntarily causing hurt: imprisonment up to 1 year "
            "or fine Rs. 1000 or both. "
            "Section 354 – Assault to outrage modesty of woman: imprisonment 1-5 years and fine. "
            "Section 375 – Rape: sexual intercourse against will, without consent, under fear, "
            "fraud, with minor under 18, or unsound mind. "
            "Section 376 – Punishment for rape: rigorous imprisonment not less than 7 years, "
            "extendable to life imprisonment, and fine. "
            "Section 376A – Death or persistent vegetative state of victim: not less than "
            "20 years to life imprisonment or death."
        ),
    },
    {
        "title": "Indian Penal Code 1860 – Offences Against State (Sections 121–130)",
        "category": "CRIMINAL",
        "jurisdiction": "India",
        "text": (
            "Section 121 – Waging or attempting to wage war against Government of India: "
            "Death or life imprisonment with fine. "
            "Section 124A – Sedition: bringing or attempting to bring hatred/contempt/disaffection "
            "towards Government by words, signs or visible representation. Punishment: life "
            "imprisonment or up to 3 years with or without fine. "
            "Section 153A – Promoting enmity between groups on grounds of religion, race, "
            "place of birth, residence, language: imprisonment up to 3 years or fine or both. "
            "Section 153B – Imputations and assertions prejudicial to national integration."
        ),
    },
    {
        "title": "Indian Penal Code 1860 – Offences Against Property (Sections 378–462)",
        "category": "CRIMINAL",
        "jurisdiction": "India",
        "text": (
            "Section 378 – Theft: dishonestly taking moveable property out of possession of any "
            "person without consent. "
            "Section 379 – Punishment for theft: imprisonment up to 3 years or fine or both. "
            "Section 383 – Extortion: putting any person in fear of injury and inducing delivery "
            "of property. "
            "Section 384 – Punishment for extortion: imprisonment up to 3 years or fine or both. "
            "Section 390 – Robbery: theft or extortion accompanied by causing or attempting "
            "death, hurt, or wrongful restraint. "
            "Section 392 – Punishment for robbery: rigorous imprisonment up to 10 years and fine. "
            "Section 395 – Punishment for dacoity (5+ persons): life imprisonment or up to "
            "10 years and fine. "
            "Section 405 – Criminal breach of trust: entrusted property dishonestly "
            "misappropriated or converted. "
            "Section 406 – Punishment for criminal breach of trust: imprisonment up to 3 years "
            "or fine or both. "
            "Section 415 – Cheating: deceiving any person to deliver property or to do/omit "
            "any act. "
            "Section 420 – Cheating and dishonestly inducing delivery of property: imprisonment "
            "up to 7 years and fine. "
            "Section 425 – Mischief: causing wrongful loss or damage to property. "
            "Section 441 – Criminal trespass: entering property in possession of another with "
            "intent to commit offence or intimidate. "
            "Section 458 – House-trespass with preparation for hurt or wrongful confinement."
        ),
    },
    {
        "title": "Bharatiya Nyaya Sanhita (BNS) 2023 – Replacement of IPC",
        "category": "CRIMINAL",
        "jurisdiction": "India",
        "text": (
            "The Bharatiya Nyaya Sanhita (BNS) 2023 replaced the Indian Penal Code 1860, "
            "effective July 1, 2024. "
            "Section 103 BNS – Murder (replaces IPC S.302): Death or life imprisonment and fine. "
            "Section 64 BNS – Rape (replaces IPC S.376): Rigorous imprisonment not less than "
            "10 years, extendable to life. "
            "Section 316 BNS – Cheating (replaces IPC S.420). "
            "Section 303 BNS – Theft (replaces IPC S.378). "
            "Section 111 BNS – Organised crime: new provision covering criminal syndicates. "
            "Section 113 BNS – Terrorist act: punishment up to death or life imprisonment. "
            "Section 69 BNS – Sexual intercourse by deceitful means: new provision. "
            "Section 152 BNS – Endangering sovereignty, unity and integrity of India (replaces "
            "Section 124A IPC sedition). "
            "Key change: Community service introduced as punishment for first-time minor offenders. "
            "Bharatiya Nagarik Suraksha Sanhita (BNSS) 2023 replaced CrPC. "
            "Bharatiya Sakshya Adhiniyam (BSA) 2023 replaced Evidence Act."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # INDIAN CONTRACT ACT 1872
    # ══════════════════════════════════════════════════════════════════════
    {
        "title": "Indian Contract Act 1872 – Formation of Contract (Sections 1–30)",
        "category": "CONTRACT",
        "jurisdiction": "India",
        "text": (
            "Section 2(a) – Proposal/Offer: signifying willingness to do or abstain from doing "
            "anything to obtain assent of another. "
            "Section 2(b) – Promise: when person to whom proposal is made signifies assent, "
            "proposal becomes a promise. "
            "Section 2(d) – Consideration: at the desire of the promisor, the promisee or any "
            "other person has done or promises to do something. "
            "Section 10 – All agreements are contracts if made by free consent of parties "
            "competent to contract, for a lawful consideration with a lawful object, not "
            "expressly declared void. "
            "Section 11 – Competent to contract: person of majority age, sound mind, and not "
            "disqualified by law. "
            "Section 13 – 'Consent' means agreeing upon the same thing in the same sense. "
            "Section 14 – Free consent: not caused by coercion, undue influence, fraud, "
            "misrepresentation, or mistake. "
            "Section 15 – Coercion: committing or threatening to commit act forbidden by IPC "
            "or unlawfully detaining property. "
            "Section 16 – Undue influence: one party in a position to dominate the will of "
            "the other and uses that position to obtain unfair advantage. "
            "Section 17 – Fraud: includes false suggestion of fact, active concealment of "
            "material fact, promise without intention to perform. "
            "Section 18 – Misrepresentation: assertion not warranted by information, breach "
            "of duty giving advantage. "
            "Section 23 – Unlawful consideration or object: forbidden by law; defeats provisions "
            "of any law; fraudulent; injurious to person/property; immoral; opposed to public "
            "policy. "
            "Section 25 – Agreement without consideration is void (exceptions: natural love and "
            "affection, compensation for past services, time-barred debt). "
            "Section 26 – Agreements in restraint of marriage are void. "
            "Section 27 – Agreements in restraint of trade are void (exception: sale of goodwill). "
            "Section 28 – Agreements in restraint of legal proceedings are void."
        ),
    },
    {
        "title": "Indian Contract Act 1872 – Performance and Breach (Sections 37–75)",
        "category": "CONTRACT",
        "jurisdiction": "India",
        "text": (
            "Section 37 – Parties must perform or offer to perform their promises. "
            "Section 39 – Refusal to perform whole promise: other party may put an end to contract. "
            "Section 56 – Agreement to do impossible act is void. Doctrine of Frustration: "
            "contract becomes void when performance becomes impossible or unlawful by some "
            "event which the promisor could not prevent. "
            "Section 62 – Effect of novation, rescission, and alteration of contract. "
            "Section 63 – Promisee may dispense with or remit performance of promise. "
            "Section 73 – Compensation for loss caused by breach of contract: party who suffers "
            "breach is entitled to receive compensation for any loss or damage caused, which "
            "naturally arose from the breach or which parties knew was likely to arise. "
            "Section 74 – Compensation for breach where penalty stipulated: party is entitled "
            "to reasonable compensation not exceeding the penalty stipulated. "
            "Section 75 – Party rightfully rescinding contract entitled to compensation."
        ),
    },
    {
        "title": "Indian Contract Act 1872 – Indemnity, Guarantee, Bailment, Agency (Sections 124–238)",
        "category": "CONTRACT",
        "jurisdiction": "India",
        "text": (
            "Section 124 – Contract of indemnity: promise to save another from loss caused by "
            "promisor or third person. "
            "Section 126 – Contract of guarantee: contract to perform promise or discharge "
            "liability of third person in case of default. Three parties: Surety, Principal "
            "Debtor, Creditor. "
            "Section 128 – Liability of surety is co-extensive with that of principal debtor. "
            "Section 133 – Variation of contract of guarantee without surety's consent discharges "
            "surety. "
            "Section 148 – Bailment: delivery of goods by one person to another for some purpose "
            "on contract that they shall be returned or disposed of. Bailor and Bailee. "
            "Section 151 – Care to be taken by bailee: care of ordinary prudent person. "
            "Section 172 – Pledge: bailment of goods as security for payment of debt. "
            "Section 182 – Agent and principal: agent employed to do any act for another or "
            "to represent another in dealings with third persons. "
            "Section 188 – Extent of agent's authority: express and implied authority. "
            "Section 190 – Agent cannot delegate to sub-agent (delegatus non potest delegare). "
            "Section 201 – Termination of agency: revocation, renunciation, completion of "
            "business, death or insanity."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # TRANSFER OF PROPERTY ACT 1882
    # ══════════════════════════════════════════════════════════════════════
    {
        "title": "Transfer of Property Act 1882 – Sale, Mortgage, Lease, Gift",
        "category": "PROPERTY",
        "jurisdiction": "India",
        "text": (
            "Section 5 – Transfer of property: act by which living person conveys property "
            "to one or more other living persons. "
            "Section 6 – Property of any kind may be transferred except: chance of heir-apparent, "
            "right of re-entry, easement, restricted interests, right to sue, public offices. "
            "Section 54 – Sale: transfer of ownership in exchange for a price paid or promised. "
            "Tangible immovable property above Rs. 100 must be transferred by registered instrument. "
            "Section 55 – Rights and liabilities of buyer and seller. "
            "Section 58 – Mortgage: transfer of interest in specific immovable property to "
            "secure payment of loan or debt. Types: Simple mortgage, Mortgage by conditional "
            "sale, Usufructuary mortgage, English mortgage, Equitable mortgage (deposit of "
            "title-deeds). "
            "Section 105 – Lease: transfer of right to enjoy immoveable property for a certain "
            "time in consideration of a price (rent). Lessor and Lessee. "
            "Section 108 – Rights and liabilities of lessor and lessee. "
            "Section 111 – Determination of lease. "
            "Section 122 – Gift: transfer of moveable or immoveable property voluntarily and "
            "without consideration. Gift of immoveable property must be by registered instrument "
            "signed by donor and attested by two witnesses. "
            "Section 123 – Transfer of property for benefit of unborn person. "
            "Section 130 – Transfer of actionable claims."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # COMPANIES ACT 2013
    # ══════════════════════════════════════════════════════════════════════
    {
        "title": "Companies Act 2013 – Incorporation, Directors, Corporate Governance",
        "category": "COMPANY",
        "jurisdiction": "India",
        "text": (
            "Section 2(20) – Company: company incorporated under this Act or previous company law. "
            "Section 2(68) – Private company: restricts share transfer, limits members to 200, "
            "prohibits public subscription. "
            "Section 3 – Formation of company: 7 or more persons (public), 2 or more (private), "
            "1 person (One Person Company). "
            "Section 4 – Memorandum of Association: name clause, registered office clause, "
            "objects clause, liability clause, capital clause. "
            "Section 7 – Incorporation: filing with Registrar of Companies. "
            "Section 9 – Effect of registration: body corporate with perpetual succession and "
            "separate legal entity. "
            "Section 149 – Board of Directors: public company minimum 3 directors, private "
            "company minimum 2, OPC minimum 1. Listed companies must have at least one-third "
            "independent directors. At least one woman director for certain classes. "
            "Section 166 – Duties of directors: act in good faith in best interests of company; "
            "exercise due care, skill and diligence; avoid conflict of interest; no undue gain. "
            "Section 173 – Board meetings: at least 4 meetings per year, gap not more than 120 days. "
            "Section 177 – Audit Committee: listed companies and prescribed others. "
            "Section 184 – Disclosure of director's interest. "
            "Section 188 – Related party transactions: require board/shareholder approval. "
            "Section 197 – Overall maximum managerial remuneration: 11% of net profits. "
            "Section 271 – Winding up by Tribunal circumstances. "
            "Section 447 – Punishment for fraud: imprisonment 6 months to 10 years and fine."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # INDIAN EVIDENCE ACT 1872
    # ══════════════════════════════════════════════════════════════════════
    {
        "title": "Indian Evidence Act 1872 – Relevancy, Admissibility, Burden of Proof",
        "category": "EVIDENCE",
        "jurisdiction": "India",
        "text": (
            "Section 3 – Evidence means oral statements and documentary evidence including "
            "electronic records. "
            "Section 5 – Evidence may be given of facts in issue and relevant facts. "
            "Section 6 – Res gestae: facts forming part of same transaction are relevant. "
            "Section 24 – Confessions caused by inducement, threat or promise are irrelevant. "
            "Section 25 – Confession to police officer is irrelevant. "
            "Section 27 – Information leading to discovery: so much as relates distinctly to "
            "fact discovered may be proved. "
            "Section 32 – Statements by persons who cannot be called as witnesses: dying "
            "declaration admissible. "
            "Section 45 – Opinions of experts are relevant (medical, handwriting, fingerprint). "
            "Section 65B – Admissibility of electronic records: certificate from person in "
            "charge of computer required. "
            "Section 101 – Burden of proof: whoever desires court to give judgment on legal "
            "right must prove the relevant facts. He who asserts must prove. "
            "Section 102 – Burden on person who would fail if no evidence given. "
            "Section 105 – Burden of proving case comes within exception is on accused. "
            "Section 114 – Court may presume existence of certain facts. "
            "Section 118 – All persons competent to testify unless prevented by tender years, "
            "old age, disease of mind. "
            "Section 132 – Witness not excused from answering incriminating questions but "
            "protected from prosecution for such answers. "
            "Section 137 – Examination-in-chief, cross-examination, re-examination. "
            "Section 138 – Order of examinations. Hostile witness: court's discretion."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # CrPC / BNSS 2023 – CRIMINAL PROCEDURE
    # ══════════════════════════════════════════════════════════════════════
    {
        "title": "Code of Criminal Procedure 1973 (CrPC) – Arrest, FIR, Bail, Trial",
        "category": "PROCEDURE",
        "jurisdiction": "India",
        "text": (
            "Section 2(c) – Cognizable offence: police may arrest without warrant. "
            "Section 2(l) – Non-cognizable offence: police require warrant to arrest. "
            "Section 41 – When police may arrest without warrant: cognizable offences with "
            "reasonable belief. "
            "Section 41A – Notice of appearance before arrest if punishment up to 7 years: "
            "arrest only if notice not complied with (Arnesh Kumar guidelines). "
            "Section 50 – Person arrested must be informed of grounds of arrest. "
            "Section 57 – Person arrested not to be detained more than 24 hours without "
            "magistrate's order. "
            "Section 154 – FIR (First Information Report): information of cognizable offence "
            "recorded in writing, signed by informant, copy given free. Mandatory registration "
            "(Lalita Kumari v. State of UP, 2014). "
            "Section 161 – Examination of witnesses by police during investigation. "
            "Section 164 – Recording of confessions and statements before Magistrate. "
            "Section 167 – When investigation cannot be completed in 24 hours: detention up "
            "to 60 days (life offences) or 90 days; default bail if charge sheet not filed. "
            "Section 173 – Charge sheet (final report) on completion of investigation. "
            "Section 436 – Bailable offences: bail as of right. "
            "Section 437 – Non-bailable offences: bail at court's discretion. "
            "Section 438 – Anticipatory bail: direction for bail to person apprehending arrest. "
            "Section 439 – Special powers of High Court or Sessions Court for bail. "
            "Section 482 – High Court's inherent powers to prevent abuse of process."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # WRITS
    # ══════════════════════════════════════════════════════════════════════
    {
        "title": "Constitutional Writs – Habeas Corpus, Mandamus, Certiorari, Prohibition, Quo Warranto",
        "category": "WRIT",
        "jurisdiction": "India",
        "text": (
            "Article 32 (Supreme Court) and Article 226 (High Courts) empower courts to issue "
            "five writs: "
            "1. Habeas Corpus ('you shall have the body'): issued to bring a detained person "
            "before court and examine legality of detention. If unlawful, immediate release "
            "ordered. Can be issued against both State and private individuals. "
            "2. Mandamus ('we command'): issued to compel public authority to perform its "
            "statutory duty. Cannot be issued against private individuals, against President "
            "or Governor, or to enforce contractual duties. "
            "3. Certiorari ('to be certified'): issued to quash decisions of inferior courts "
            "or tribunals made with excess of jurisdiction, violation of natural justice, or "
            "errors of law apparent on face of record. "
            "4. Prohibition: issued to prevent inferior courts or tribunals from exceeding "
            "jurisdiction. Preventive in nature; issued before decision. "
            "5. Quo Warranto ('by what authority'): issued to enquire into legality of claim "
            "to public office. Can be sought by any member of public. Prevents illegal "
            "occupation of public office."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # IT ACT 2000 & DPDP ACT 2023
    # ══════════════════════════════════════════════════════════════════════
    {
        "title": "Information Technology Act 2000 – Cybercrimes and Digital Evidence",
        "category": "CYBER",
        "jurisdiction": "India",
        "text": (
            "Section 4 – Legal recognition of electronic records. "
            "Section 5 – Legal recognition of digital signatures. "
            "Section 43 – Penalty for damage to computer or computer system: up to Rs. 1 crore. "
            "Section 43A – Compensation for failure to protect data by body corporate. "
            "Section 65 – Tampering with computer source documents: imprisonment up to 3 years "
            "or fine Rs. 2 lakh. "
            "Section 66 – Computer related offences (dishonest/fraudulent acts): imprisonment "
            "up to 3 years or fine Rs. 5 lakh. "
            "Section 66C – Identity theft: imprisonment up to 3 years and fine Rs. 1 lakh. "
            "Section 66D – Cheating by personation using computer: imprisonment up to 3 years "
            "and fine Rs. 1 lakh. "
            "Section 66E – Violation of privacy (intimate images): imprisonment up to 3 years "
            "or fine. "
            "Section 66F – Cyber terrorism: life imprisonment. "
            "Section 67 – Obscene material in electronic form: imprisonment up to 3 years and "
            "fine. "
            "Section 69 – Power to intercept, monitor, or decrypt information by government. "
            "Section 79 – Safe harbour for intermediaries: not liable for third-party content "
            "if due diligence followed. "
            "Digital Personal Data Protection Act 2023: Rights of data principals: access, "
            "correction, erasure, grievance redressal. Data fiduciaries must implement security "
            "safeguards, notify breaches, obtain valid consent. Penalties up to Rs. 250 crore. "
            "Data Protection Board of India established."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # CONSUMER PROTECTION ACT 2019
    # ══════════════════════════════════════════════════════════════════════
    {
        "title": "Consumer Protection Act 2019 – Rights, Deficiency, Commissions",
        "category": "CONSUMER",
        "jurisdiction": "India",
        "text": (
            "Section 2(7) – Consumer: person who buys goods or hires services for consideration; "
            "does not include persons buying for resale. "
            "Section 2(11) – Deficiency: fault, imperfection or shortcoming in quality required "
            "to be maintained by law or under contract. "
            "Section 2(47) – Unfair trade practice: practice adopting unfair or deceptive methods "
            "to promote sale. "
            "Six consumer rights: right to be protected; right to be informed; right to choose; "
            "right to be heard; right to seek redressal; right to consumer education. "
            "Consumer Disputes Redressal Commissions: District Commission (claims up to Rs. 1 "
            "crore), State Commission (Rs. 1-10 crore), National Commission (above Rs. 10 crore). "
            "Section 35 – Complaint before District Commission within 2 years of cause of action. "
            "Section 39 – Relief: remove defects, replace goods, return price, compensate loss, "
            "discontinue unfair practice, withdraw hazardous goods. "
            "Central Consumer Protection Authority (CCPA): regulates unfair trade practices, "
            "false or misleading advertisements. "
            "Section 89 – False or misleading advertisements: fine up to Rs. 10 lakh, "
            "imprisonment up to 2 years."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # RIGHT TO INFORMATION ACT 2005
    # ══════════════════════════════════════════════════════════════════════
    {
        "title": "Right to Information Act 2005 – Access to Information",
        "category": "RTI",
        "jurisdiction": "India",
        "text": (
            "Section 2(f) – Information: any material in any form including records, documents, "
            "memos, e-mails, opinions, orders, logbooks, data in electronic form. "
            "Section 2(h) – Public authority: authority established by Constitution, Parliament, "
            "State Legislature, or Government notification; includes NGOs substantially financed "
            "by Government. "
            "Section 3 – All citizens shall have the right to information. "
            "Section 4 – Proactive disclosure obligations of public authorities: maintain and "
            "publish categories of information including organisation, functions, rules, "
            "regulations, records. "
            "Section 6 – Request for information to Public Information Officer (PIO). "
            "Section 7 – PIO must provide information within 30 days; 48 hours if life or "
            "liberty is at stake. "
            "Section 8 – Exemptions: information affecting sovereignty/security; information in "
            "fiduciary capacity; trade secrets; cabinet papers; personal information causing "
            "invasion of privacy. "
            "Section 11 – Third party information: prior intimation to third party. "
            "Section 19 – First appeal to designated officer within 30 days; second appeal "
            "to Information Commission within 90 days. "
            "Section 20 – Penalty: Rs. 250 per day up to Rs. 25,000 and disciplinary action "
            "for failure to provide information."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # TORT LAW
    # ══════════════════════════════════════════════════════════════════════
    {
        "title": "Law of Torts in India – Negligence, Nuisance, Defamation, Strict/Absolute Liability",
        "category": "TORT",
        "jurisdiction": "India",
        "text": (
            "Negligence: requires (1) duty of care owed to plaintiff, (2) breach of duty, "
            "(3) causation, (4) damage suffered. Donoghue v Stevenson [1932] – neighbour "
            "principle. Res ipsa loquitur: inference of negligence when thing under exclusive "
            "control of defendant and accident would not have occurred without negligence. "
            "Medical negligence in India (Jacob Mathew v State of Punjab, 2005): simple lack "
            "of care is civil negligence; rashness and gross negligence can be criminal. "
            "Strict Liability (Rylands v Fletcher 1868): person bringing hazardous thing on "
            "land liable if it escapes. Exceptions: act of God, plaintiff's default, consent, "
            "statutory authority, act of third party. "
            "Absolute Liability (MC Mehta v Union of India 1987): enterprise engaged in "
            "hazardous activity is absolutely liable with NO exceptions. Greater wealth means "
            "greater liability. This is stricter than English strict liability. "
            "Private Nuisance: unlawful interference with person's use or enjoyment of land. "
            "Public Nuisance: interference with right of public generally (also criminal). "
            "Defamation: publication of false statement lowering reputation of plaintiff. "
            "Libel (written), Slander (spoken). Defences: truth/justification, fair comment "
            "on public interest, privilege (absolute or qualified). "
            "Vicarious Liability: employer liable for torts of employee done in course of "
            "employment. Master-servant relationship, act within scope of employment."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # LANDMARK SUPREME COURT JUDGMENTS
    # ══════════════════════════════════════════════════════════════════════
    {
        "title": "Landmark Supreme Court Judgments of India",
        "category": "CONSTITUTIONAL",
        "jurisdiction": "India",
        "text": (
            "Kesavananda Bharati v. State of Kerala (1973): Basic structure doctrine — Parliament "
            "can amend Constitution but cannot destroy its basic structure. "
            "Maneka Gandhi v. Union of India (1978): Article 21 requires procedure to be fair, "
            "just and reasonable. Expanded right to life. "
            "Vishaka v. State of Rajasthan (1997): Guidelines on sexual harassment at workplace "
            "(now replaced by POSH Act 2013). "
            "Navtej Singh Johar v. Union of India (2018): Section 377 IPC decriminalized for "
            "consensual same-sex relations between adults. "
            "Justice K.S. Puttaswamy v. Union of India (2017): Right to Privacy is a fundamental "
            "right under Article 21 (9-judge bench, unanimous). "
            "Indra Sawhney v. Union of India (1992): Upheld 27% OBC reservation; total "
            "reservations cannot exceed 50%; creamy layer concept. "
            "S.R. Bommai v. Union of India (1994): Secularism is basic feature; President's Rule "
            "under Article 356 is subject to judicial review. "
            "MC Mehta v. Union of India (1987): Absolute liability for hazardous industries; "
            "pioneered PIL for environmental protection. "
            "Olga Tellis v. Bombay Municipal Corporation (1985): Right to livelihood is part "
            "of right to life under Article 21. "
            "Arnesh Kumar v. State of Bihar (2014): Guidelines for arrest — police must apply "
            "mind before arresting in cases punishable up to 7 years. "
            "Lalita Kumari v. State of UP (2014): Registration of FIR mandatory when information "
            "discloses cognizable offence. "
            "Shreya Singhal v. Union of India (2015): Section 66A IT Act struck down as "
            "unconstitutional for violating freedom of speech."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # FAMILY LAW
    # ══════════════════════════════════════════════════════════════════════
    {
        "title": "Hindu Marriage Act 1955 & Hindu Succession Act 1956 (amended 2005)",
        "category": "FAMILY",
        "jurisdiction": "India",
        "text": (
            "Hindu Marriage Act 1955: "
            "Section 5 – Conditions for valid Hindu marriage: neither party has living spouse; "
            "both capable of giving valid consent; groom at least 21, bride at least 18; not "
            "within prohibited degrees of relationship. "
            "Section 9 – Restitution of conjugal rights. "
            "Section 10 – Judicial separation. "
            "Section 11 – Void marriages: bigamy; within prohibited degrees. "
            "Section 12 – Voidable marriages: impotency; unsound mind; consent by fraud or force; "
            "pregnant by another person. "
            "Section 13 – Grounds for divorce: adultery; cruelty; desertion (2 years); conversion "
            "to another religion; incurable insanity; leprosy or venereal disease; renounced "
            "world; not heard of as alive for 7 years. "
            "Section 13B – Divorce by mutual consent: 1 year separation, joint petition, "
            "6-month cooling period. "
            "Hindu Succession Act 1956 (amended 2005): "
            "Section 6 – Coparcenary property: daughters have equal rights as sons in ancestral "
            "property (amendment 2005, affirmed in Vineeta Sharma v Rakesh Sharma 2020). "
            "Section 8 – General rules of succession for males: Class I heirs first. "
            "Section 14 – Property of female Hindu to be her absolute property. "
            "Section 15 – General rules of succession in case of female Hindus."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # INTELLECTUAL PROPERTY
    # ══════════════════════════════════════════════════════════════════════
    {
        "title": "Intellectual Property Law in India – Patents, Trademarks, Copyright",
        "category": "IP",
        "jurisdiction": "India",
        "text": (
            "Patents Act 1970 (amended 2005): "
            "Section 2(1)(j) – Invention: new product or process involving inventive step and "
            "capable of industrial application. "
            "Section 3 – Non-patentable inventions: frivolous; scientific principles; mathematical "
            "methods; computer programs per se; aesthetic creations; methods of treatment; plants "
            "and animals; traditional knowledge. "
            "Section 3(d) – New use of known substance not patentable (Novartis v Union of India "
            "2013: evergreening rejected). "
            "Section 48 – Rights of patentee: exclusive right to prevent third parties from "
            "making, using, selling patented product. "
            "Section 84 – Compulsory licensing available if: not reasonably available; not at "
            "reasonable price; not worked in India. Term: 20 years from filing. "
            "Trademarks Act 1999: "
            "Section 2(1)(zb) – Trademark: mark capable of graphical representation and "
            "capable of distinguishing goods/services. "
            "Section 29 – Infringement of registered trademark. "
            "Section 30 – Limits on effect of registered trademark (honest concurrent use). "
            "Copyright Act 1957: "
            "Section 14 – Copyright: exclusive right to reproduce, issue copies, perform, "
            "translate, adapt a work. "
            "Section 17 – First owner of copyright is the author; employer owns copyright "
            "of works made in course of employment. "
            "Section 22 – Term of copyright: life of author plus 60 years. "
            "Section 52 – Fair dealing: research, private study, review, criticism, reporting "
            "current events does not infringe copyright."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # ENVIRONMENTAL LAW
    # ══════════════════════════════════════════════════════════════════════
    {
        "title": "Environmental Law in India – Key Acts and Principles",
        "category": "ENVIRONMENT",
        "jurisdiction": "India",
        "text": (
            "Environment Protection Act 1986: Central government empowered to take measures "
            "to protect and improve quality of environment; set standards for emissions and "
            "discharges; restrict industrial operations; inspect premises. "
            "Water (Prevention and Control of Pollution) Act 1974: Established Central and "
            "State Pollution Control Boards; standards for water quality; prohibition on "
            "polluting water bodies. "
            "Air (Prevention and Control of Pollution) Act 1981: Standards for ambient air "
            "quality; prohibition on emissions beyond standards. "
            "Forest Conservation Act 1980: Prior approval of Central Government required for "
            "diversion of forest land for non-forest purposes. "
            "Wildlife Protection Act 1972: Protection of wild animals and plants; Schedules "
            "with varying protection levels; Project Tiger 1973. "
            "National Green Tribunal Act 2010: NGT for fast disposal of environmental cases; "
            "powers of civil court; compensation and restoration orders. "
            "Precautionary Principle: when threats of serious or irreversible damage exist, "
            "lack of full scientific certainty shall not be used as reason for postponing "
            "cost-effective measures. "
            "Polluter Pays Principle: environmental costs shall be borne by those who cause "
            "pollution. "
            "Public Trust Doctrine (MC Mehta v Kamal Nath 1997): State is trustee of natural "
            "resources — rivers, forests, seashores, air — held in trust for public use."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # LABOUR & EMPLOYMENT LAW
    # ══════════════════════════════════════════════════════════════════════
    {
        "title": "Labour and Employment Law in India – Key Statutes",
        "category": "EMPLOYMENT",
        "jurisdiction": "India",
        "text": (
            "Industrial Disputes Act 1947: "
            "Section 2(k) – Industrial dispute: any dispute connected with employment, "
            "conditions of employment, or labour. "
            "Section 10 – Reference of dispute to Labour Court/Industrial Tribunal. "
            "Section 25F – Conditions precedent to retrenchment: 1 month notice or notice pay; "
            "retrenchment compensation at 15 days wages for each completed year of service. "
            "Section 25N – Retrenchment in industrial establishments employing 100+ workers "
            "requires prior permission of appropriate government. "
            "Payment of Wages Act 1936: wages must be paid in current coin or currency, "
            "within prescribed time (7th or 10th of following month). "
            "Minimum Wages Act 1948: appropriate government to fix minimum wages for scheduled "
            "employments. "
            "Payment of Gratuity Act 1972: gratuity payable to employee who has rendered "
            "continuous service of 5 years, at 15 days wages for each completed year. "
            "Maximum gratuity: Rs. 20 lakh. "
            "Employees Provident Fund and Miscellaneous Provisions Act 1952: 12% contribution "
            "from both employer and employee. "
            "Maternity Benefit Act 1961 (amended 2017): 26 weeks paid maternity leave for "
            "establishments with 10+ employees. "
            "Sexual Harassment of Women at Workplace (POSH) Act 2013: Internal Complaints "
            "Committee (ICC) mandatory for establishments with 10+ employees. "
            "Code on Wages 2019, Code on Industrial Relations 2020, Code on Social Security 2020, "
            "Code on Occupational Safety 2020 consolidate 29 labour laws."
        ),
    },

    # ══════════════════════════════════════════════════════════════════════
    # BANKING & FINANCE LAW
    # ══════════════════════════════════════════════════════════════════════
    {
        "title": "Banking Law in India – RBI Act, Banking Regulation Act, SARFAESI, IBC",
        "category": "BANKING",
        "jurisdiction": "India",
        "text": (
            "Reserve Bank of India Act 1934: RBI established as central bank; issues currency; "
            "controls credit; banker to government. "
            "Banking Regulation Act 1949: Regulates and supervises banking companies; "
            "licensing of banks; maintenance of CRR and SLR; powers of RBI over banks. "
            "SARFAESI Act 2002 (Securitisation and Reconstruction of Financial Assets and "
            "Enforcement of Security Interest): Banks and financial institutions can enforce "
            "security interest without court intervention after 60 days notice to borrower. "
            "Debt Recovery Tribunal (DRT) and DRAT for recovery of debts above Rs. 20 lakh. "
            "Insolvency and Bankruptcy Code 2016 (IBC): "
            "Single law for insolvency of individuals, partnership firms, companies. "
            "Corporate Insolvency Resolution Process (CIRP): 180 days (extendable to 270 days) "
            "to resolve insolvency. "
            "Committee of Creditors (CoC) approves resolution plan. "
            "Liquidation if no plan approved. "
            "Section 14 – Moratorium: once CIRP initiated, moratorium on legal proceedings "
            "against corporate debtor. "
            "Prevention of Money Laundering Act 2002 (PMLA): attachment and forfeiture of "
            "proceeds of crime; Enforcement Directorate has powers of search, seizure, arrest. "
            "KYC (Know Your Customer) norms: mandatory for all banking relationships."
        ),
    },
]


def chunk_text(text, chunk_size=350, overlap=40):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i: i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def main():
    print("=" * 60)
    print("LegalMind — Legal Corpus Ingestion")
    print(f"Backend dir: {BACKEND_DIR}")
    print("=" * 60)

    # ── import app modules ────────────────────────────────────────────
    try:
        from app.vector_store.faiss_store import FAISSVectorStore
        from app.embedding.generator import EmbeddingGenerator
        from app.config.settings import get_settings
        print("[OK] App modules imported")
    except ImportError as e:
        print(f"[ERR] Cannot import app modules: {e}")
        sys.exit(1)

    # ── Supabase setup ────────────────────────────────────────────────
    try:
        from supabase import create_client
        SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
        SUPABASE_KEY = (
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or
            os.environ.get("SUPABASE_KEY", "")
        )
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("[WARN] Supabase credentials missing — skipping Supabase sync")
            db = None
        else:
            db = create_client(SUPABASE_URL, SUPABASE_KEY)
            print(f"[OK] Supabase connected")
    except Exception as e:
        print(f"[WARN] Supabase init failed: {e}")
        db = None

    # ── initialise vector store and embedder ─────────────────────────
    try:
        settings = get_settings()
        vector_store_path = str(settings.vector_store_path)
        print(f"[OK] Vector store path: {vector_store_path}")
    except Exception as e:
        vector_store_path = os.path.join(BACKEND_DIR, "data", "vector_store")
        print(f"[WARN] Could not read settings ({e}), using default: {vector_store_path}")

    vs = FAISSVectorStore(dimension=384)
    vs.load(vector_store_path)
    print(f"[OK] FAISS loaded — current count: {vs.count()} vectors")

    embedder = EmbeddingGenerator(model_name="all-MiniLM-L6-v2")
    print(f"[OK] Embedding model loaded (dim={embedder.dimension})")

    total_chunks = 0
    total_docs = 0

    for doc in LEGAL_CORPUS:
        title = doc["title"]
        category = doc["category"]
        jurisdiction = doc["jurisdiction"]
        full_text = doc["text"]

        print(f"\n[+] {title[:72]}")

        chunks = chunk_text(full_text, chunk_size=350, overlap=40)
        print(f"    chunks: {len(chunks)}")

        doc_id = str(uuid.uuid4())

        # ── Supabase documents table ──────────────────────────────────
        if db is not None:
            try:
                db.table("documents").upsert({
                    "id": doc_id,
                    "title": title,
                    "category": category,
                    "jurisdiction": jurisdiction,
                    "content": full_text[:6000],
                    "source": "legal_corpus_ingestion",
                    "metadata": json.dumps({
                        "category": category,
                        "jurisdiction": jurisdiction
                    }),
                }).execute()
            except Exception as e:
                print(f"    [WARN] Supabase doc insert: {e}")

        # ── embed and add to FAISS ────────────────────────────────────
        try:
            import numpy as np
            embeddings = embedder.embed_texts(chunks)  # shape (n, 384)

            chunk_ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
            doc_ids = [doc_id] * len(chunks)
            metadatas = [
                {
                    "title": title,
                    "category": category,
                    "jurisdiction": jurisdiction,
                    "chunk_index": i,
                    "source": "legal_corpus",
                }
                for i in range(len(chunks))
            ]

            vs.add(
                chunk_ids=chunk_ids,
                document_ids=doc_ids,
                contents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            total_chunks += len(chunks)
            print(f"    added {len(chunks)} vectors (total so far: {vs.count()})")

        except Exception as e:
            print(f"    [ERR] embedding/add failed: {e}")
            import traceback; traceback.print_exc()

        total_docs += 1

    # ── save ──────────────────────────────────────────────────────────
    try:
        vs.save(vector_store_path)
        print(f"\n[OK] FAISS index saved to {vector_store_path}")
    except Exception as e:
        print(f"\n[ERR] vs.save() failed: {e}")

    print("\n" + "=" * 60)
    print(f"DONE — {total_docs} documents, {total_chunks} new chunks")
    print(f"Total vectors in store: {vs.count()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
