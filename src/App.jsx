import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import "./App.css";
import VoiceAssistant from "./components/VoiceAssistant";
import HealthProfile from "./components/HealthProfile";
import SchemeComparison from "./components/SchemeComparison";
import HospitalMap from "./components/HospitalMap";
import ImageAssistant from "./components/ImageAssistant";
import LocationPermissionCard from "./components/LocationPermissionCard";
import {
  getSchemeRecommendations,
  checkProfileEligibility,
  requestPasswordReset,
  confirmPasswordReset,
  getNearbyHospitals,
  reverseGeocodeLocation,
  API_BASE_URL,
} from "./services/aiService";
import { t } from "./translations";


const LANGUAGES = [
  { code: "en-IN", label: "English (India)" },
  { code: "ta-IN", label: "தமிழ் (Tamil)" },
  { code: "te-IN", label: "తెలుగు (Telugu)" },
  { code: "ml-IN", label: "മലയാളം (Malayalam)" },
];

const HEALTH_GUIDANCE_ITEMS = [
  {
    id: "fever",
    title: {
      "en-IN": "Acute Fever & Body Pain",
      "ta-IN": "காய்ச்சல் & உடல் வலி மேலாண்மை",
      "te-IN": "తీవ్ర జ్వరం & ఒళ్ళు నొప్పులు",
      "ml-IN": "പനിയും ശരീരവേദനയും പരിചരണം",
    },
    indicates: {
      "en-IN": "Commonly occurs with seasonal viral infection, flu, or mild inflammation.",
      "ta-IN": "பருவகால வைரஸ் தொற்று, சளி அல்லது ஆரம்ப நிலை தொற்று காரணமாக ஏற்படுகிறது.",
      "te-IN": "సాధారణంగా వైరల్ ఇన్ఫెక్షన్, జలుబు లేదా అలసట వల్ల వస్తుంది.",
      "ml-IN": "വൈറൽ അണുബാധ, ജലദോഷം അല്ലെങ്കിൽ സീസണൽ പനി മൂലം ഉണ്ടാകുന്നു.",
    },
    safeCare: {
      "en-IN": [
        "Adequate physical rest in a well-ventilated room",
        "Drink plenty of clean boiled water, ORS, tender coconut, or light kanji",
        "Lukewarm water sponging on forehead and neck if temperature is high",
        "Wear light, comfortable cotton clothing",
      ],
      "ta-IN": [
        "நல்ல காற்றோட்டமுள்ள அறையில் போதுமான ஓய்வு எடுக்கவும்",
        "சுத்தமான காய்ச்சிய நீர், ORS, இளநீர் அல்லது கஞ்சி குடிக்கவும்",
        "காய்ச்சல் அதிகமாக இருந்தால் நெற்றி மற்றும் கழுத்தில் வெதுவெதுப்பான நீர் ஒத்தடம் கொடுக்கவும்",
        "லேசான பருத்தி ஆடைகளை அணியவும்",
      ],
      "te-IN": [
        "గాలి ప్రసరించే గదిలో తగినంత విశ్రాంతి తీసుకోండి",
        "కాచి చల్లార్చిన నీరు, ORS, కొబ్బరి నీళ్ళు లేదా గంజి ఎక్కువగా తాగండి",
        "జ్వరం ఎక్కువగా ఉంటే నుదురు మరియు మెడపై గోరువెచ్చని నీటితో తడి గుడ్డ పెట్టండి",
        "తేలికపాటి కాటన్ దుస్తులు ధరించండి",
      ],
      "ml-IN": [
        "നല്ല വായുസഞ്ചാരമുള്ള മുറിയിൽ ആവശ്യത്തിന് വിശ്രമിക്കുക",
        "തിളപ്പിച്ചാറിയ വെള്ളം, ORS, ഇളനീർ അല്ലെങ്കിൽ കഞ്ഞി ധാരാളം കുടിക്കുക",
        "പനി കൂടുതലാണെങ്കിൽ നെറ്റിയിലും കഴുത്തിലും ചെറുചൂടുവെള്ളത്തിൽ തുണി നനച്ചു തുടയ്ക്കുക",
        "കനം കുറഞ്ഞ കോട്ടൺ വസ്ത്രങ്ങൾ ധരിക്കുക",
      ],
    },
    warningSigns: {
      "en-IN": [
        "Fever continuing beyond 3 days without relief",
        "Difficulty breathing or persistent chest discomfort",
        "Inability to retain liquids or severe vomiting",
      ],
      "ta-IN": [
        "3 நாட்களுக்கு மேல் காய்ச்சல் நீடித்தால்",
        "சுவாசிப்பதில் சிரமம் அல்லது நெஞ்சு வலி",
        "தண்ணீர் கூட குடிக்க முடியாத தீவிர வாந்தி",
      ],
      "te-IN": [
        "3 రోజులకు మించి జ్వరం తగ్గకపోవడం",
        "శ్వాస తీసుకోవడంలో ఇబ్బంది లేదా ఛాతీలో అసౌకర్యం",
        "తీవ్రమైన వాంతులు లేదా నీరు కూడా తాగలేకపోవడం",
      ],
      "ml-IN": [
        "3 ദിവസത്തിൽ കൂടുതൽ പനി നീണ്ടുനിൽക്കുക",
        "ശ്വാസമെടുക്കാൻ ബുദ്ധിമുട്ട് അല്ലെങ്കിൽ നെഞ്ചുവേദന",
        "തുടർച്ചയായ ഛർദ്ദി കാരണം വെള്ളം പോലും കുടിക്കാൻ കഴിയാതെ വരിക",
      ],
    },
    query: {
      "en-IN": "I have had a high fever and body pain for 2 days. What supportive home care should I follow?",
      "ta-IN": "எனக்கு 2 நாட்களாக கடுமையான காய்ச்சல் மற்றும் உடல்வலி உள்ளது. என்ன முதலுதவி செய்ய வேண்டும்?",
      "te-IN": "నాకు 2 రోజులుగా తీవ్రమైన జ్వరం మరియు ఒళ్ళు నొప్పులు ఉన్నాయి. ఏమి చేయాలి?",
      "ml-IN": "എനിക്ക് 2 ദിവസമായി കടുത്ത പനിയും ശരീരവേദനയും ഉണ്ട്. എന്ത് ചെയ്യണം?",
    },
  },
  {
    id: "cough",
    title: {
      "en-IN": "Cough & Sore Throat",
      "ta-IN": "இருமல் & தொண்டை வலி மேலாண்மை",
      "te-IN": "దగ్గు & గొంతు నొప్పి సంరక్షణ",
      "ml-IN": "ചുമയും തൊണ്ടവേദനയും സുരക്ഷിത പരിചരണം",
    },
    indicates: {
      "en-IN": "Usually caused by upper respiratory viral exposure, dust allergies, or cold dry weather.",
      "ta-IN": "சுவாசப்பாதை தொற்று, தூசி ஒவ்வாமை அல்லது வறண்ட வானிலை காரணமாக ஏற்படுகிறது.",
      "te-IN": "శ్వాసకోశ ఇన్ఫెక్షన్ లేదా దుమ్ము అలర్జీ వల్ల వస్తుంది.",
      "ml-IN": "ശ്വാസകോശ അണുബാധ അല്ലെങ്കിൽ അലർജി മൂലം ഉണ്ടാകുന്നു.",
    },
    safeCare: {
      "en-IN": [
        "Warm water gargle with a pinch of salt 3 times daily",
        "Steam inhalation with clean plain warm water",
        "Warm fluids like herbal decoction (Kabasura / ginger tea)",
        "Avoid cold, chilled drinks and dry, dusty environments",
      ],
      "ta-IN": [
        "ஒரு சிட்டிகை உப்புடன் வெதுவெதுப்பான நீரில் தினமும் 3 வேளை வாய் கொப்பளிக்கவும்",
        "வெதுவெதுப்பான சுத்தமான தண்ணீரில் ஆவி பிடிக்கவும்",
        "கபசுர குடிநீர் அல்லது இஞ்சி தேநீர் போன்ற சூடான திரவங்களை அருந்தவும்",
        "குளிர்ந்த பானங்கள் மற்றும் தூசி நிறைந்த இடங்களைத் தவிர்க்கவும்",
      ],
      "te-IN": [
        "చిటికెడు ఉప్పు వేసిన గోరువెచ్చని నీటితో రోజుకు 3 సార్లు పుక్కిలించండి",
        "శుభ్రమైన నీటితో ఆవిరి పట్టండి",
        "అల్లం టీ లేదా కషాయం వంటి వెచ్చని ద్రవాలను తీసుకోండి",
        "చల్లని పానీయాలు మరియు దుమ్ము వాతావరణానికి దూరంగా ఉండండి",
      ],
      "ml-IN": [
        "ചെറുചൂടുവെള്ളത്തിൽ ഉപ്പിട്ട് ദിവസത്തിൽ 3 തവണ തൊണ്ട കുലുക്കുഴിയുക",
        "ശുദ്ധമായ ചൂടുവെള്ളത്തിൽ ആവി പിടിക്കുക",
        "ഇഞ്ചി ചായയോ കഷായമോ പോലെയുള്ള ചൂടുള്ള പാനീയങ്ങൾ കുടിക്കുക",
        "തണുത്ത പാനീയങ്ങളും പൊടിപടലങ്ങളും ഒഴിവാക്കുക",
      ],
    },
    warningSigns: {
      "en-IN": [
        "Blood in sputum or coughing fit causing breathlessness",
        "High fever lasting over 48 hours",
        "Audible wheezing or chest tightness",
      ],
      "ta-IN": [
        "சளியில் இரத்தம் வருவது அல்லது மூச்சுத் திணறல்",
        "48 மணி நேரத்திற்கு மேல் நீடிக்கும் அதிக காய்ச்சல்",
        "மூச்சு வாங்குதல் அல்லது நெஞ்சு இறுக்கம்",
      ],
      "te-IN": [
        "కఫంలో రక్తం పడటం లేదా తీవ్రమైన ఆయాసం",
        "48 గంటలకు మించి అధిక జ్వరం ఉండటం",
        "శ్వాసలో పిల్లికూతలు లేదా ఛాతీ పట్టేయడం",
      ],
      "ml-IN": [
        "കഫത്തിൽ രക്തം കാണപ്പെടുകയോ ശ്വാസതടസ്സം അനുഭവപ്പെടുകയോ ചെയ്യുക",
        "48 മണിക്കൂറിൽ കൂടുതൽ കടുത്ത പനി നീണ്ടുനിൽക്കുക",
        "ശ്വാസംമുട്ടൽ അല്ലെങ്കിൽ നെഞ്ചിൽ വിമ്മിഷ്ടം",
      ],
    },
    query: {
      "en-IN": "I have a persistent cough and sore throat. What safe home remedies can I follow?",
      "ta-IN": "எனக்கு வறட்டு இருமல் மற்றும் தொண்டை வலி உள்ளது. பாதுகாப்பான வீட்டு வைத்தியம் என்ன?",
      "te-IN": "నాకు పొడి దగ్గు మరియు గొంతు నొప్పి ఉంది. సురక్షిత గృహ చిట్కాలు ఏమిటి?",
      "ml-IN": "എനിക്ക് വിട്ടുമാറാത്ത ചുമയും തൊണ്ടവേദനയും ഉണ്ട്. വീട്ടിൽ ചെയ്യാവുന്ന പരിചരണങ്ങൾ എന്തൊക്കെയാണ്?",
    },
  },
  {
    id: "stomach",
    title: {
      "en-IN": "Stomach Pain & Diarrhea",
      "ta-IN": "வயிற்று வலி & வயிற்றுப்போக்கு",
      "te-IN": "కడుపు నొప్పి & విరేచనాలు",
      "ml-IN": "വയറുവേദനയും വയറിളക്കവും",
    },
    indicates: {
      "en-IN": "Commonly related to food contamination, acute gastroenteritis, or mild indigestion.",
      "ta-IN": "உணவு ஒவ்வாமை, செரிமானக் கோளாறு அல்லது பாக்டீரியா தொற்று காரணமாக ஏற்படுகிறது.",
      "te-IN": "ఆహార లోపాలు లేదా జీర్ణకోశ ఇన్ఫెక్షన్ వల్ల వస్తుంది.",
      "ml-IN": "ഭക്ഷണ അലർജി അല്ലെങ്കിൽ ദഹനക്കേട് മൂലം ഉണ്ടാകുന്നു.",
    },
    safeCare: {
      "en-IN": [
        "Immediately prepare and drink standard WHO ORS solution after every loose stool",
        "Eat light, easily digestible food (steamed idli, curd rice, banana)",
        "Maintain hand hygiene before eating and after using washroom",
        "Do NOT take self-prescribed anti-diarrheal pills without doctor advice",
      ],
      "ta-IN": [
        "ஒவ்வொரு முறை கழிப்பறை சென்ற பிறகும் ORS கரைசல் குடிக்கவும்",
        "எளிதில் செரிமானமாகும் இட்லி, தயிர் சாதம் அல்லது வாழைப்பழம் சாப்பிடவும்",
        "உணவுக்கு முன்பும், கழிப்பறை சென்ற பின்பும் கைகளை சோப்பால் கழுவவும்",
        "மருத்துவர் ஆலோசனையின்றி மாத்திரைகளை சுயமாக உட்கொள்ள வேண்டாம்",
      ],
      "te-IN": [
        "ప్రతి విరేచనం తర్వాత వెంటనే ORS ద్రవాన్ని తాగండి",
        "సులభంగా జీర్ణమయ్యే ఇడ్లీ, పెరుగన్నం లేదా అరటిపండు తీసుకోండి",
        "చేతులను శుభ్రంగా కడుక్కోండి",
        "వైద్యుడి సలహా లేకుండా మాత్రలు వేసుకోవద్దు",
      ],
      "ml-IN": [
        "ഓരോ തവണ വയറിളകുമ്പോഴും ORS ലായനി കുടിക്കുക",
        "എളുപ്പം ദഹിക്കുന്ന ഇഡ്ഡലി, തൈരുസാദം, ഏത്തപ്പഴം എന്നിവ കഴിക്കുക",
        "ഭക്ഷണത്തിന് മുൻപും ശേഷവും കൈകൾ വൃത്തിയായി കഴുകുക",
        "ഡോക്ടറുടെ നിർദ്ദേശമില്ലാതെ സ്വയം മരുന്നുകൾ കഴിക്കരുത്",
      ],
    },
    warningSigns: {
      "en-IN": [
        "Signs of severe dehydration (dry mouth, sunken eyes, no urine for 6 hours)",
        "Blood in stools or continuous vomiting",
        "Severe acute abdominal cramping",
      ],
      "ta-IN": [
        "தீவிர நீரிழப்பு (வறண்ட வாய், கண்கள் குழிவிழுதல், 6 மணி நேரம் சிறுநீர் வராமை)",
        "மலத்தில் இரத்தம் அல்லது தொடர் வாந்தி",
        "கடுமையான தாங்க முடியாத வயிற்று வலி",
      ],
      "te-IN": [
        "తీవ్ర డీహైడ్రేషన్ లక్షణాలు (నోరు ఎండిపోవడం, 6 గంటలుగా మూత్రం రాకపోవడం)",
        "మలంలో రక్తం లేదా నిరంతర వాంతులు",
        "తీవ్రమైన కడుపు నొప్పి",
      ],
      "ml-IN": [
        "കടുത്ത നിർജ്ജലീകരണം (വായ വരൾച്ച, 6 മണിക്കൂറായി മൂത്രം പോകാതിരിക്കുക)",
        "മലത്തിൽ രക്തം അല്ലെങ്കിൽ നിർത്താതെയുള്ള ഛർദ്ദി",
        "കഠിനമായ വയറുവേദന",
      ],
    },
    query: {
      "en-IN": "I have acute stomach pain and nausea. What immediate steps should I take?",
      "ta-IN": "எனக்கு கடுமையான வயிற்று வலி மற்றும் வாந்தி வருகிறது. என்ன செய்ய வேண்டும்?",
      "te-IN": "నాకు విపరీతమైన కడుపు నొప్పి మరియు వాంతులు అవుతున్నాయి. ఏమి చేయాలి?",
      "ml-IN": "എനിക്ക് കഠിനമായ വയറുവേദനയും ഛർദ്ദിയും ഉണ്ട്. എന്ത് ചെയ്യണം?",
    },
  },
  {
    id: "dizziness",
    title: {
      "en-IN": "Dizziness & Heat Exhaustion",
      "ta-IN": "தலைச்சுற்றல் & வெப்ப சோர்வு",
      "te-IN": "తలతిరుగుడు & వడదెబ్బ సంరక్షణ",
      "ml-IN": "തലകറക്കവും ക്ഷീണവും",
    },
    indicates: {
      "en-IN": "Often linked to mild dehydration, low blood sugar, sudden standing, or heat stress.",
      "ta-IN": "நீரிழப்பு, குறைந்த இரத்த சர்க்கரை அல்லது வெயிலின் தாக்கம் காரணமாக ஏற்படுகிறது.",
      "te-IN": "డీహైడ్రేషన్ లేదా రక్తపోటు హెచ్చుతగ్గుల వల్ల వస్తుంది.",
      "ml-IN": "നിർജ്ജലീകരണം അല്ലെങ്കിൽ ക്ഷീണം മൂലം ഉണ്ടാകുന്നു.",
    },
    safeCare: {
      "en-IN": [
        "Sit or lie down immediately in a cool, shaded place",
        "Sip electrolyte fluids, lemon water with a pinch of salt and sugar",
        "Loosen tight clothing and rest with feet slightly elevated",
        "Avoid sudden postural changes from lying to standing",
      ],
      "ta-IN": [
        "உடனடியாக குளிர்ந்த, நிழலான இடத்தில் அமரவும் அல்லது படுக்கவும்",
        "உப்பு மற்றும் சர்க்கரை கலந்த எலுமிச்சை சாறு அல்லது ORS குடிக்கவும்",
        "இறுக்கமான ஆடைகளைத் தளர்த்தி கால்களை சற்று உயர்த்தி ஓய்வெடுக்கவும்",
        "திடீரென எழுந்து நிற்பதைத் தவிர்க்கவும்",
      ],
      "te-IN": [
        "వెంటనే చల్లని, నీడ ఉన్న ప్రదేశంలో కూర్చోండి లేదా పడుకోండి",
        "నిమ్మకాయ నీరు, ఉప్పు-చక్కెర ద్రావణం లేదా ORS తాగండి",
        "బిగుతుగా ఉన్న దుస్తులను వదులు చేసి కాళ్ళను కొద్దిగా పైకి ఉంచండి",
        "పడుకుని ఉన్నప్పుడు ఒక్కసారిగా పైకి లేవకండి",
      ],
      "ml-IN": [
        "തണലുള്ള തണുത്ത സ്ഥലത്ത് ഉടൻ ഇരിക്കുകയോ കിടക്കുകയോ ചെയ്യുക",
        "ഉപ്പും പഞ്ചസാരയും ചേർത്ത നാരങ്ങാവെള്ളമോ ORS ലായനിയോ കുടിക്കുക",
        "ഇറുകിയ വസ്ത്രങ്ങൾ അയച്ച് കാലുകൾ അല്പം ഉയർത്തി വെക്കുക",
        "പെട്ടെന്ന് എഴുന്നേറ്റു നിൽക്കുന്നത് ഒഴിവാക്കുക",
      ],
    },
    warningSigns: {
      "en-IN": [
        "Fainting, loss of consciousness, or slurred speech",
        "Chest discomfort or sudden weakness in one side of body",
        "Rapid, irregular heartbeat",
      ],
      "ta-IN": [
        "மயக்கம், சுயநினைவு இழப்பு அல்லது பேச தடுமாறுதல்",
        "நெஞ்சு வலி அல்லது உடலின் ஒரு பக்கத்தில் பலவீனம்",
        "அதிவேக அல்லது ஒழுங்கற்ற இதயத் துடிப்பு",
      ],
      "te-IN": [
        "స్పృహ తప్పడం లేదా మాట తడబడటం",
        "ఛాతీలో నొప్పి లేదా శరీరంలో ఒక వైపు బలహീనత",
        "క్రమరహిత గుండె వేగం",
      ],
      "ml-IN": [
        "ബോധക്ഷയം അല്ലെങ്കിൽ സംസാരിക്കാൻ പ്രയാസം",
        "നെഞ്ചുവേദന അല്ലെങ്കിൽ ശരീരത്തിന്റെ ഒരു വശത്ത് തളർച്ച",
        "അസാധാരണമായ നെഞ്ചിടിപ്പ്",
      ],
    },
    query: {
      "en-IN": "I feel dizzy and exhausted. What could be the cause and what should I do?",
      "ta-IN": "எனக்கு திடீரென தலைச்சுற்றல் மற்றும் சோர்வு ஏற்படுகிறது. என்ன காரணம் மற்றும் என்ன செய்ய வேண்டும்?",
      "te-IN": "నాకు తీవ్రమైన తలతిరుగుడు మరియు అలసటగా ఉంది. కారణం ఏమిటి మరియు ఏమి చేయాలి?",
      "ml-IN": "എനിക്ക് കഠിനമായ തലകറക്കവും ക്ഷീണവും അനുഭവപ്പെടുന്നു. എന്ത് ചെയ്യണം?",
    },
  },
];

function getStoredProfile() {
  try {
    const stored = localStorage.getItem("arogya_patient_profile");
    if (!stored) {
      return {
        state: "Tamil Nadu",
        district: "Salem",
        taluk: "Salem Taluk",
        locality: "Shevapet",
        pincode: "636001",
        latitude: 11.6508,
        longitude: 78.1402,
      };
    }
    return JSON.parse(stored);
  } catch {
    return {
      state: "Tamil Nadu",
      district: "Salem",
      taluk: "Salem Taluk",
      locality: "Shevapet",
      pincode: "636001",
      latitude: 11.6508,
      longitude: 78.1402,
    };
  }
}

function getStoredLanguage() {
  try {
    const stored = localStorage.getItem("arogya_app_language");
    if (stored && ["en-IN", "ta-IN", "te-IN", "ml-IN"].includes(stored)) {
      return stored;
    }
    return "en-IN";
  } catch {
    return "en-IN";
  }
}

function getProfileCompletion(profile = {}) {
  const fields = [
    profile.age,
    profile.gender,
    profile.state,
    profile.district,
    profile.income_range || profile.annual_income,
    profile.occupation,
    profile.is_pregnant,
    profile.has_child,
    profile.is_elderly,
    profile.health_conditions?.length,
  ];

  const completed = fields.filter((v) => v !== undefined && v !== null && v !== "" && v !== false && v !== 0).length;
  return Math.min(100, Math.round((completed / 10) * 100));
}

function getGreeting(langCode = "en-IN") {
  const hour = new Date().getHours();
  if (hour < 12) return t("greetingMorning", langCode);
  if (hour < 18) return t("greetingAfternoon", langCode);
  return t("greetingEvening", langCode);
}

function getLocalizedState(state, langCode) {
  const stateKeys = {
    "Tamil Nadu": "stateTamilNadu",
    "Andhra Pradesh": "stateAndhraPradesh",
    Kerala: "stateKerala",
    National: "stateAllIndia",
  };
  return t(stateKeys[state] || "stateAllIndia", langCode);
}

function getLocalizedStatus(status, langCode) {
  const key = {
    "likely eligible": "statusLikelyEligible",
    "possibly eligible": "statusPossiblyEligible",
    "more information needed": "statusMoreInfoNeeded",
    "not determined": "statusNotDetermined",
  }[String(status || "").toLowerCase()];
  return key ? t(key, langCode) : status || t("statusMoreInfoNeeded", langCode);
}

function App() {
  // Post-login persistent language selection
  const [selectedLang, setSelectedLang] = useState(getStoredLanguage);
  const [profile, setProfile] = useState(getStoredProfile);

  // Authentication State (Starts strictly in English)
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authUser, setAuthUser] = useState(null);
  const [isGuest, setIsGuest] = useState(() => {
    try {
      return sessionStorage.getItem("arogya_guest_session") === "true";
    } catch {
      return false;
    }
  });
  const [authMode, setAuthMode] = useState("login"); // "login" | "signup"
  const [authForm, setAuthForm] = useState({ name: "", email: "", password: "", confirmPassword: "" });
  const [authError, setAuthError] = useState("");
  const [authSuccessNotice, setAuthSuccessNotice] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Read any reset token from URL once during initial load
  const initialUrlToken = useMemo(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      return params.get("reset_token") || params.get("token") || "";
    } catch {
      return "";
    }
  }, []);

  // Forgot / Reset Password Modal State
  const [showForgotModal, setShowForgotModal] = useState(() => Boolean(initialUrlToken));
  const [forgotStep, setForgotStep] = useState(() => (initialUrlToken ? 2 : 1)); // 1 = Enter Email, 2 = Set New Password, 3 = Success
  const [forgotEmail, setForgotEmail] = useState("");
  const [resetToken, setResetToken] = useState(() => initialUrlToken);
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [showResetNewPassword, setShowResetNewPassword] = useState(false);
  const [showResetConfirmPassword, setShowResetConfirmPassword] = useState(false);
  const [forgotBusy, setForgotBusy] = useState(false);
  const [forgotError, setForgotError] = useState("");

  // App Navigation & Modals
  // "home" | "voice" | "guidance" | "hospitals" | "schemes" | "eligibility" | "compare"
  const [activeView, setActiveView] = useState("home");
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [selectedScheme, setSelectedScheme] = useState(null);
  const [recommendedCards, setRecommendedCards] = useState([]);
  const [schemesLoading, setSchemesLoading] = useState(false);

  // Eligibility evaluation state
  const [eligibilityData, setEligibilityData] = useState(null);
  const [eligibilityLoading, setEligibilityLoading] = useState(false);
  const [eligibilityError, setEligibilityError] = useState("");
  const isEvaluatingEligibilityRef = useRef(false);

  // Nearby Hospitals State
  const [hospitals, setHospitals] = useState([]);
  const [hospitalsLoading, setHospitalsLoading] = useState(false);
  const [hospitalsError, setHospitalsError] = useState("");
  const [selectedDistrict, setSelectedDistrict] = useState(() => profile.district || profile.location || "Salem");
  const [searchRadiusKm, setSearchRadiusKm] = useState(10);
  const [userHierarchyLocation, setUserHierarchyLocation] = useState(() => ({
    state: profile.state || "Tamil Nadu",
    district: profile.district || "Salem",
    taluk: profile.taluk || "Salem Taluk",
    locality: profile.locality || "Shevapet",
    pincode: profile.pincode || "636001",
  }));

  const [selectedHospitalDetail, setSelectedHospitalDetail] = useState(null);
  const [gpsLocationActive, setGpsLocationActive] = useState(false);
  const [userGPSCoords, setUserGPSCoords] = useState(null);
  const [userLocationMeta, setUserLocationMeta] = useState(null);
  const [locationPermissionNotice, setLocationPermissionNotice] = useState("");

  const profileCompletion = useMemo(() => getProfileCompletion(profile), [profile]);
  const userState = profile.state || "Tamil Nadu";

  // Automatically sync district when profile location updates
  useEffect(() => {
    if (profile?.district && !gpsLocationActive && selectedDistrict !== profile.district) {
      setSelectedDistrict(profile.district);
      setUserHierarchyLocation({
        state: profile.state || "Tamil Nadu",
        district: profile.district,
        taluk: profile.taluk || "",
        locality: profile.locality || "",
        pincode: profile.pincode || "",
      });
    }
  }, [profile, gpsLocationActive, selectedDistrict]);

  // Handle language change with persistence
  const handleLanguageChange = (newLang) => {
    setSelectedLang(newLang);
    localStorage.setItem("arogya_app_language", newLang);
  };

  // Check existing session on mount
  useEffect(() => {
    try {
      if (sessionStorage.getItem("arogya_guest_session") === "true") {
        setIsGuest(true);
        setAuthUser({ name: "Guest Citizen", email: "", isGuest: true, role: "guest" });
        setIsAuthenticated(true);
        return;
      }
    } catch (e) {
      console.warn("Guest session check error:", e);
    }

    const token = localStorage.getItem("arogya_auth_token");
    if (!token) return;

    fetch(`${API_BASE_URL}/api/auth/session`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error("session expired");
        return res.json();
      })
      .then((data) => {
        setIsGuest(false);
        setAuthUser(data.user);
        setIsAuthenticated(true);
        if (data.user.profile && Object.keys(data.user.profile).length > 0) {
          const next = { ...getStoredProfile(), ...data.user.profile };
          setProfile(next);
          localStorage.setItem("arogya_patient_profile", JSON.stringify(next));
        }
      })
      .catch(() => {
        localStorage.removeItem("arogya_auth_token");
        setIsAuthenticated(false);
      });
  }, []);

  // Fetch Recommended Schemes when authenticated or profile/language changes
  useEffect(() => {
    if (!isAuthenticated) return;

    let isMounted = true;

    getSchemeRecommendations(profile, "", selectedLang, userState, 4)
      .then((data) => {
        if (!isMounted) return;
        const recommendations = data.recommendations || [];
        setRecommendedCards(recommendations);
      })
      .catch((err) => {
        console.warn("Could not fetch recommended schemes:", err);
      })
      .finally(() => {
        if (isMounted) setSchemesLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isAuthenticated, profile, selectedLang, userState]);

  // Fetch Nearby Hospitals following location priority: Current GPS -> Hierarchical Saved Profile -> Manual location
  const fetchNearbyHospitals = useCallback(
    async ({
      lat = null,
      lon = null,
      state = null,
      district = null,
      taluk = null,
      locality = null,
      pincode = null,
      location = null,
      radius_km = null,
    } = {}) => {
      setHospitalsLoading(true);
      setHospitalsError("");
      try {
        const queryLat = lat !== null ? lat : userGPSCoords?.latitude;
        const queryLon = lon !== null ? lon : userGPSCoords?.longitude;
        const queryState = state !== null ? state : (queryLat ? "" : (userHierarchyLocation?.state || profile?.state || "Tamil Nadu"));
        const queryDistrict = district !== null ? district : (queryLat ? "" : (userHierarchyLocation?.district || selectedDistrict || profile?.district || "Salem"));
        const queryTaluk = taluk !== null ? taluk : (queryLat ? "" : (userHierarchyLocation?.taluk || profile?.taluk || ""));
        const queryLocality = locality !== null ? locality : (queryLat ? "" : (userHierarchyLocation?.locality || profile?.locality || ""));
        const queryPincode = pincode !== null ? pincode : (queryLat ? "" : (userHierarchyLocation?.pincode || profile?.pincode || ""));
        const queryRadius = radius_km !== null ? radius_km : searchRadiusKm;

        const data = await getNearbyHospitals({
          latitude: queryLat,
          longitude: queryLon,
          state: queryState,
          district: queryDistrict === "All Tamil Nadu" ? "" : queryDistrict,
          taluk: queryTaluk,
          locality: queryLocality,
          pincode: queryPincode,
          location: location,
          radius_km: queryRadius,
          limit: 15,
        });

        setHospitals(data.hospitals || []);
        setUserLocationMeta(data.user_location || null);
      } catch (err) {
        setHospitalsError(err.message || "Failed to load hospitals.");
      } finally {
        setHospitalsLoading(false);
      }
    },
    [userGPSCoords, userHierarchyLocation, selectedDistrict, profile, searchRadiusKm]
  );

  const handleOpenHospitals = useCallback((district = selectedDistrict) => {
    setActiveView("hospitals");
    fetchNearbyHospitals({ district });
  }, [selectedDistrict, fetchNearbyHospitals]);

  // Request browser geolocation for nearby hospitals
  const handleRequestGPSLocation = () => {
    if (!navigator.geolocation) {
      setLocationPermissionNotice("Geolocation is not supported by your browser. Using saved profile location.");
      return;
    }

    setHospitalsLoading(true);
    setHospitalsError("");
    setLocationPermissionNotice("Detecting high-accuracy GPS position...");

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;
        setUserGPSCoords({ latitude, longitude });
        setGpsLocationActive(true);

        try {
          const rev = await reverseGeocodeLocation({ latitude, longitude });
          if (rev) {
            setUserHierarchyLocation({
              state: rev.state || "Tamil Nadu",
              district: rev.district || "Salem",
              taluk: rev.taluk || "",
              locality: rev.locality || "",
              pincode: rev.pincode || "",
            });
            setSelectedDistrict(rev.district || "Salem");
            setLocationPermissionNotice(`GPS active: ${rev.display_name || `${latitude.toFixed(4)}°, ${longitude.toFixed(4)}°`}`);
          }
        } catch {
          setLocationPermissionNotice(`GPS active: ${latitude.toFixed(4)}°, ${longitude.toFixed(4)}°`);
        }

        fetchNearbyHospitals({ lat: latitude, lon: longitude, radius_km: searchRadiusKm });
      },
      (err) => {
        console.warn("Geolocation access denied or unavailable:", err);
        setGpsLocationActive(false);
        setUserGPSCoords(null);
        const fallbackDistrict = profile?.district || selectedDistrict || "Salem";

        setLocationPermissionNotice(`Location access not granted. Using saved profile location (${fallbackDistrict}).`);
        setHospitalsLoading(false);
        fetchNearbyHospitals({ district: fallbackDistrict, radius_km: searchRadiusKm });
      },
      { timeout: 8000, enableHighAccuracy: true }
    );
  };

  // Auth Submit
  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError("");
    setAuthSuccessNotice("");

    if (authMode === "signup" && authForm.password !== authForm.confirmPassword) {
      setAuthError("Passwords do not match.");
      return;
    }

    if (authForm.password.length < 6) {
      setAuthError("Password must be at least 6 characters.");
      return;
    }

    setAuthBusy(true);

    try {
      const endpoint = authMode === "signup" ? "/api/auth/signup" : "/api/auth/login";
      const payload =
        authMode === "signup"
          ? { name: authForm.name, email: authForm.email, password: authForm.password }
          : { email: authForm.email, password: authForm.password };

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!response.ok) {
        let errorMsg = data.detail || "Authentication failed.";
        if (response.status === 401 || errorMsg.toLowerCase().includes("incorrect") || errorMsg.toLowerCase().includes("invalid")) {
          errorMsg = "Invalid email or password. Please check your credentials or reset your password.";
        } else if (response.status === 404 || errorMsg.toLowerCase().includes("not found")) {
          errorMsg = "Authentication service is currently unavailable. Please verify your connection.";
        }
        throw new Error(errorMsg);
      }

      try {
        sessionStorage.removeItem("arogya_guest_session");
      } catch {}
      setIsGuest(false);
      localStorage.setItem("arogya_auth_token", data.session_token);
      setAuthUser(data.user);
      setIsAuthenticated(true);
      setAuthForm({ name: "", email: "", password: "", confirmPassword: "" });

      if (data.user.profile && Object.keys(data.user.profile).length > 0) {
        const next = { ...getStoredProfile(), ...data.user.profile };
        setProfile(next);
        localStorage.setItem("arogya_patient_profile", JSON.stringify(next));
      }
    } catch (err) {
      setAuthError(err.message || "Authentication failed.");
    } finally {
      setAuthBusy(false);
    }
  };

  // Forgot Password: Step 1 (Request Token)
  const handleRequestResetToken = async (e) => {
    e.preventDefault();
    setForgotError("");
    if (!forgotEmail || !forgotEmail.trim()) {
      setForgotError("Please enter your registered email address.");
      return;
    }

    setForgotBusy(true);
    try {
      const res = await requestPasswordReset(forgotEmail.trim());
      setResetToken(res.reset_token || "");
      setForgotStep(2);
    } catch (err) {
      setForgotError(err.message || "Could not find an account with this email.");
    } finally {
      setForgotBusy(false);
    }
  };

  // Forgot Password: Step 2 (Submit New Password)
  const handleConfirmPasswordReset = async (e) => {
    e.preventDefault();
    setForgotError("");

    if (newPassword !== confirmNewPassword) {
      setForgotError("New passwords do not match.");
      return;
    }

    if (newPassword.length < 6) {
      setForgotError("Password must be at least 6 characters.");
      return;
    }

    setForgotBusy(true);
    try {
      await confirmPasswordReset(resetToken, newPassword);
      setForgotStep(3);
      setAuthSuccessNotice("Password updated successfully! Please log in with your new password.");
      setAuthForm((prev) => ({ ...prev, email: forgotEmail, password: "" }));
    } catch (err) {
      setForgotError(err.message || "Failed to update password. Token may have expired.");
    } finally {
      setForgotBusy(false);
    }
  };

  const handleCloseForgotModal = () => {
    setShowForgotModal(false);
    setForgotStep(1);
    setForgotError("");
    setNewPassword("");
    setConfirmNewPassword("");
    setResetToken("");
  };

  // Continue without login (Guest Session)
  const handleContinueWithoutLogin = () => {
    try {
      sessionStorage.setItem("arogya_guest_session", "true");
    } catch {}
    setIsGuest(true);
    setAuthUser({
      name: "Guest Citizen",
      email: "",
      isGuest: true,
      role: "guest",
    });
    setAuthError("");
    setAuthSuccessNotice("");
    setIsAuthenticated(true);
    setActiveView("home");
  };

  const handleLogout = () => {
    try {
      sessionStorage.removeItem("arogya_guest_session");
    } catch {}
    setIsGuest(false);
    const token = localStorage.getItem("arogya_auth_token");
    if (token) {
      fetch(`${API_BASE_URL}/api/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => {});
    }

    localStorage.removeItem("arogya_auth_token");
    setIsAuthenticated(false);
    setAuthUser(null);
    setAuthError("");
    setActiveView("home");
  };

  // Sync profile changes to state & backend
  const handleProfileUpdate = async (nextProfile) => {
    setProfile(nextProfile);
    localStorage.setItem("arogya_patient_profile", JSON.stringify(nextProfile));
    setEligibilityData(null); // Invalidate cached eligibility so fresh profile details trigger immediate recalculation

    if (isGuest) return; // Guest sessions store clinical criteria in localStorage, zero backend account modification

    const token = localStorage.getItem("arogya_auth_token");
    if (!token) return;

    try {
      await fetch(`${API_BASE_URL}/api/profile/save`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ profile: nextProfile }),
      });
    } catch (err) {
      console.warn("Profile sync error:", err);
    }
  };

  // Run Eligibility API Evaluation (Fixing Blank Screen Bug)
  const handleRunEligibility = async () => {
    setActiveView("eligibility");
    setEligibilityLoading(true);
    setEligibilityError("");
    try {
      const data = await checkProfileEligibility(profile);
      setEligibilityData(data);
    } catch (err) {
      console.error("Eligibility evaluation error:", err);
      setEligibilityError(err.message || "Could not evaluate eligibility. Please check your network and try again.");
    } finally {
      setEligibilityLoading(false);
    }
  };

  // Auto-evaluate eligibility when navigating to the Eligibility view if not yet loaded
  useEffect(() => {
    if (activeView === "eligibility" && !eligibilityData && !isEvaluatingEligibilityRef.current) {
      isEvaluatingEligibilityRef.current = true;
      setEligibilityLoading(true);
      setEligibilityError("");
      checkProfileEligibility(profile)
        .then((data) => {
          if (data) {
            setEligibilityData(data);
          }
        })
        .catch((err) => {
          console.error("Eligibility evaluation error:", err);
          setEligibilityError(err?.message || "Could not evaluate eligibility. Please check your network and try again.");
        })
        .finally(() => {
          setEligibilityLoading(false);
          isEvaluatingEligibilityRef.current = false;
        });
    }
  }, [activeView, eligibilityData, profile]);



  const applyPresetFromHome = (presetKey) => {
    let nextProfile = { ...profile };

    if (presetKey === "pregnancy") {
      nextProfile = {
        ...nextProfile,
        age: "24",
        gender: "female",
        state: "Tamil Nadu",
        district: "Madurai",
        annual_income: 96000,
        income_range: "< 1.2L",
        family_size: "3",
        is_pregnant: true,
        occupation: "Homemaker",
      };
    } else if (presetKey === "low_income") {
      nextProfile = {
        ...nextProfile,
        age: "42",
        gender: "male",
        state: "Tamil Nadu",
        district: "Salem",
        annual_income: 84000,
        income_range: "< 1.2L",
        family_size: "4",
        has_child: true,
        health_conditions: ["hypertension"],
        occupation: "Agricultural Worker",
      };
    } else if (presetKey === "senior") {
      nextProfile = {
        ...nextProfile,
        age: "68",
        gender: "male",
        state: "Tamil Nadu",
        district: "Coimbatore",
        annual_income: 72000,
        income_range: "< 1.2L",
        family_size: "2",
        is_elderly: true,
        health_conditions: ["hypertension", "diabetes"],
        occupation: "Retired",
      };
    } else if (presetKey === "pensioner") {
      nextProfile = {
        ...nextProfile,
        age: "64",
        gender: "female",
        state: "Kerala",
        district: "Thiruvananthapuram",
        annual_income: 180000,
        income_range: "1.2L - 3.0L",
        family_size: "2",
        is_elderly: true,
        occupation: "Pensioner",
      };
    }

    handleProfileUpdate(nextProfile);
  };

  // Helper to safely extract scheme title from multilingual dict or string
  const getSchemeTitle = (nameObj, fallbackId = "") => {
    if (!nameObj) return fallbackId;
    if (typeof nameObj === "string") return nameObj;
    const tag = selectedLang.startsWith("ta")
      ? "ta"
      : selectedLang.startsWith("te")
      ? "te"
      : selectedLang.startsWith("ml")
      ? "ml"
      : "en";
    return nameObj[tag] || nameObj.en || fallbackId;
  };

  // Categorize eligibility schemes safely
  const categorizedEligibility = useMemo(() => {
    if (!eligibilityData?.schemes) return { likely: [], possible: [], infoNeeded: [] };

    const likely = [];
    const possible = [];
    const infoNeeded = [];

    for (const s of eligibilityData.schemes) {
      const status = (s.eligibility_status || "").toLowerCase();
      if (status.includes("likely")) {
        likely.push(s);
      } else if (status.includes("possib")) {
        possible.push(s);
      } else {
        infoNeeded.push(s);
      }
    }

    return { likely, possible, infoNeeded };
  }, [eligibilityData]);

  // ==========================================
  // 1. AUTHENTICATION SCREEN (Fully Localized)
  // ==========================================
  if (!isAuthenticated) {
    return (
      <div className="auth-shell">
        <div className="auth-card">
          {/* Top Row: Language Selector */}
          <div style={{ display: "flex", justifyContent: "flex-end", width: "100%", marginBottom: "4px" }}>
            <div className="lang-selector-wrap">
              <select
                id="auth-language-select"
                className="lang-select"
                value={selectedLang}
                onChange={(e) => handleLanguageChange(e.target.value)}
                aria-label="Select Language"
              >
                {LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.label}
                  </option>
                ))}
              </select>
              <span className="lang-chevron" aria-hidden="true">▼</span>
            </div>
          </div>

          <div className="auth-header">
            <div className="auth-logo-badge">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
              </svg>
            </div>
            <h1 className="auth-title">{t("authTitle", selectedLang)}</h1>
            <div className="auth-subtitle">{t("authSubtitle", selectedLang)}</div>
            <p className="auth-tagline">{t("authTagline", selectedLang)}</p>
          </div>

          <div className="auth-mode-tabs">
            <button
              type="button"
              className={`auth-tab-btn ${authMode === "login" ? "active" : ""}`}
              onClick={() => { setAuthMode("login"); setAuthError(""); setAuthSuccessNotice(""); }}
            >
              {t("login", selectedLang)}
            </button>
            <button
              type="button"
              className={`auth-tab-btn ${authMode === "signup" ? "active" : ""}`}
              onClick={() => { setAuthMode("signup"); setAuthError(""); setAuthSuccessNotice(""); }}
            >
              {t("createAccount", selectedLang)}
            </button>
          </div>

          <form className="auth-form" onSubmit={handleAuthSubmit}>
            {authMode === "signup" && (
              <div className="field-group">
                <label className="field-label" htmlFor="auth-name">{t("fullName", selectedLang)}</label>
                <input
                  id="auth-name"
                  type="text"
                  className="field-input"
                  value={authForm.name}
                  onChange={(e) => setAuthForm((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder={t("name", selectedLang)}
                  required
                />
              </div>
            )}

            <div className="field-group">
              <label className="field-label" htmlFor="auth-email">{t("email", selectedLang)}</label>
              <input
                id="auth-email"
                type="email"
                className="field-input"
                value={authForm.email}
                onChange={(e) => setAuthForm((prev) => ({ ...prev, email: e.target.value }))}
                placeholder="you@example.com"
                required
              />
            </div>

            <div className="field-group">
              <label className="field-label" htmlFor="auth-password">{t("password", selectedLang)}</label>
              <div className="field-input-wrap">
                <input
                  id="auth-password"
                  type={showPassword ? "text" : "password"}
                  className="field-input password-input"
                  value={authForm.password}
                  onChange={(e) => setAuthForm((prev) => ({ ...prev, password: e.target.value }))}
                  placeholder={t("minimumPassword", selectedLang)}
                  required
                />
                <button
                  type="button"
                  className="password-toggle-btn"
                  onClick={() => setShowPassword((prev) => !prev)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
              <span className="field-help-text">{t("passwordRequirements", selectedLang)}</span>
            </div>

            {authMode === "signup" && (
              <div className="field-group">
                <label className="field-label" htmlFor="auth-confirm">{t("confirmPassword", selectedLang)}</label>
                <div className="field-input-wrap">
                  <input
                    id="auth-confirm"
                    type={showConfirmPassword ? "text" : "password"}
                    className="field-input password-input"
                    value={authForm.confirmPassword}
                    onChange={(e) => setAuthForm((prev) => ({ ...prev, confirmPassword: e.target.value }))}
                    placeholder={t("reEnterPassword", selectedLang)}
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() => setShowConfirmPassword((prev) => !prev)}
                    aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                  >
                    {showConfirmPassword ? (
                      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                        <line x1="1" y1="1" x2="23" y2="23" />
                      </svg>
                    ) : (
                      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>
            )}

            {authSuccessNotice && (
              <div className="auth-success-banner">
                <span>✓</span>
                <span>{authSuccessNotice}</span>
              </div>
            )}

            {authError && (
              <div className="auth-error-banner">
                <span>⚠️</span>
                <span>{authError}</span>
              </div>
            )}

            <button type="submit" className="btn-primary-auth" disabled={authBusy}>
              {authBusy ? t("verifying", selectedLang) : authMode === "login" ? t("login", selectedLang) : t("createAccount", selectedLang)}
            </button>

            {authMode === "login" && (
              <button
                type="button"
                id="continue-without-login-btn"
                className="btn-guest-auth"
                onClick={handleContinueWithoutLogin}
              >
                <span>👤</span>
                <span>{t("continueWithoutLogin", selectedLang) || "Continue without login"}</span>
              </button>
            )}

            <div className="auth-secondary-actions">
              {authMode === "login" && (
                <button
                  type="button"
                  className="forgot-password-link"
                  onClick={() => {
                    setForgotEmail(authForm.email);
                    setShowForgotModal(true);
                  }}
                >
                  {t("forgotPassword", selectedLang)}
                </button>
              )}

              <div className="switch-auth-mode-text">
                {authMode === "login" ? t("dontHaveAccount", selectedLang) : t("alreadyHaveAccount", selectedLang)}
                <button
                  type="button"
                  className="switch-auth-mode-btn"
                  onClick={() => {
                    setAuthMode(authMode === "login" ? "signup" : "login");
                    setAuthError("");
                    setAuthSuccessNotice("");
                  }}
                >
                  {authMode === "login" ? t("createAccount", selectedLang) : t("login", selectedLang)}
                </button>
              </div>
            </div>
          </form>
        </div>

        {/* Forgot Password Modal (Multilingual) */}
        {showForgotModal && (
          <div className="modal-overlay" onClick={handleCloseForgotModal}>
            <div className="modal-dialog forgot-password-dialog" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h3 className="modal-title">{t("resetPasswordTitle", selectedLang)}</h3>
                <button type="button" className="modal-close-btn" onClick={handleCloseForgotModal} aria-label={t("close", selectedLang)}>
                  ✕
                </button>
              </div>

              <div className="modal-body">
                {forgotStep === 1 && (
                  <form onSubmit={handleRequestResetToken} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                    <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)", lineHeight: "1.5" }}>
                      {t("enterRegisteredEmailPrompt", selectedLang)}
                    </p>
                    <div className="field-group">
                      <label className="field-label" htmlFor="forgot-email">{t("registeredEmail", selectedLang)}</label>
                      <input
                        id="forgot-email"
                        type="email"
                        className="field-input"
                        value={forgotEmail}
                        onChange={(e) => setForgotEmail(e.target.value)}
                        placeholder="you@example.com"
                        required
                      />
                    </div>

                    {forgotError && (
                      <div className="auth-error-banner">
                        <span>⚠️</span>
                        <span>{forgotError}</span>
                      </div>
                    )}

                    <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "8px" }}>
                      <button type="button" className="header-action-btn" onClick={handleCloseForgotModal}>
                        {t("close", selectedLang)}
                      </button>
                      <button type="submit" className="btn-primary-auth" style={{ width: "auto" }} disabled={forgotBusy}>
                        {forgotBusy ? t("verifying", selectedLang) : `${t("sendResetToken", selectedLang)} →`}
                      </button>
                    </div>
                  </form>
                )}

                {forgotStep === 2 && (
                  <form onSubmit={handleConfirmPasswordReset} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                    <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)", lineHeight: "1.5" }}>
                      {t("resetPasswordDesc", selectedLang)} (<strong>{forgotEmail}</strong>)
                    </p>

                    <div className="field-group">
                      <label className="field-label">{t("resetTokenLabel", selectedLang)}</label>
                      <input
                        type="text"
                        className="field-input"
                        value={resetToken}
                        onChange={(e) => setResetToken(e.target.value)}
                        placeholder="Paste reset token"
                        required
                      />
                    </div>

                    <div className="field-group">
                      <label className="field-label" htmlFor="reset-new-password">{t("newPassword", selectedLang)}</label>
                      <div className="field-input-wrap">
                        <input
                          id="reset-new-password"
                          type={showResetNewPassword ? "text" : "password"}
                          className="field-input password-input"
                          value={newPassword}
                          onChange={(e) => setNewPassword(e.target.value)}
                          placeholder={t("minimumPassword", selectedLang)}
                          required
                        />
                        <button
                          type="button"
                          className="password-toggle-btn"
                          onClick={() => setShowResetNewPassword((p) => !p)}
                        >
                          {showResetNewPassword ? "👁️" : "🔒"}
                        </button>
                      </div>
                    </div>

                    <div className="field-group">
                      <label className="field-label" htmlFor="reset-confirm-password">{t("confirmNewPassword", selectedLang)}</label>
                      <div className="field-input-wrap">
                        <input
                          id="reset-confirm-password"
                          type={showResetConfirmPassword ? "text" : "password"}
                          className="field-input password-input"
                          value={confirmNewPassword}
                          onChange={(e) => setConfirmNewPassword(e.target.value)}
                          placeholder={t("reEnterPassword", selectedLang)}
                          required
                        />
                        <button
                          type="button"
                          className="password-toggle-btn"
                          onClick={() => setShowResetConfirmPassword((p) => !p)}
                        >
                          {showResetConfirmPassword ? "👁️" : "🔒"}
                        </button>
                      </div>
                    </div>

                    {forgotError && (
                      <div className="auth-error-banner">
                        <span>⚠️</span>
                        <span>{forgotError}</span>
                      </div>
                    )}

                    <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "8px" }}>
                      <button type="button" className="header-action-btn" onClick={() => setForgotStep(1)}>
                        ← {t("back", selectedLang)}
                      </button>
                      <button type="submit" className="btn-primary-auth" style={{ width: "auto" }} disabled={forgotBusy}>
                        {forgotBusy ? t("verifying", selectedLang) : t("updatePassword", selectedLang)}
                      </button>
                    </div>
                  </form>
                )}

                {forgotStep === 3 && (
                  <div style={{ textAlign: "center", padding: "16px 0" }}>
                    <div style={{ fontSize: "2.4rem", marginBottom: "8px" }}>✓</div>
                    <h4 style={{ color: "var(--success-color)", marginBottom: "8px" }}>{t("passwordUpdated", selectedLang)}</h4>
                    <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)", marginBottom: "16px" }}>
                      {t("passwordUpdated", selectedLang)}
                    </p>
                    <button type="button" className="btn-primary-auth" onClick={handleCloseForgotModal}>
                      {t("backToLogin", selectedLang)}
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ==========================================
  // 2. MAIN APPLICATION (Authenticated)
  // ==========================================
  return (
    <div className="app-container">
      {/* HEADER: Exactly ONE header across all routed views */}
      <header className="app-header">
        <div className="header-inner">
          {/* Brand */}
          <div className="header-brand" onClick={() => setActiveView("home")} role="button" tabIndex={0}>
            <div className="brand-icon-box">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
              </svg>
            </div>
            <div className="brand-text">
              <span className="brand-title">AROGYA NEXUS</span>
              <span className="brand-subtitle">{t("appSubtitle", selectedLang)}</span>
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="header-nav" aria-label="Main Navigation">
            <button
              type="button"
              className={`header-nav-btn ${activeView === "home" ? "active" : ""}`}
              onClick={() => setActiveView("home")}
            >
              {t("home", selectedLang)}
            </button>
            <button
              type="button"
              className={`header-nav-btn ${activeView === "voice" ? "active" : ""}`}
              onClick={() => setActiveView("voice")}
            >
              {t("arogya", selectedLang)}
            </button>
            <button
              type="button"
              className={`header-nav-btn ${activeView === "image" ? "active" : ""}`}
              onClick={() => setActiveView("image")}
            >
              {t("imageNav", selectedLang)}
            </button>
            <button
              type="button"
              className={`header-nav-btn ${activeView === "guidance" ? "active" : ""}`}
              onClick={() => setActiveView("guidance")}
            >
              {t("guidanceNav", selectedLang)}
            </button>
            <button
              type="button"
              className={`header-nav-btn ${activeView === "hospitals" ? "active" : ""}`}
              onClick={() => handleOpenHospitals()}
            >
              {t("hospitalsNav", selectedLang)}
            </button>
            <button
              type="button"
              className={`header-nav-btn ${activeView === "schemes" ? "active" : ""}`}
              onClick={() => setActiveView("schemes")}
            >
              {t("schemes", selectedLang)}
            </button>
            <button
              type="button"
              className={`header-nav-btn ${activeView === "eligibility" ? "active" : ""}`}
              onClick={handleRunEligibility}
            >
              {t("eligibility", selectedLang)}
            </button>
          </nav>

          {/* Header Controls (Language, Profile, Logout) */}
          <div className="header-actions">
            {/* Multilingual Selector */}
            <div className="lang-selector-wrap">
              <select
                className="lang-select"
                value={selectedLang}
                onChange={(e) => handleLanguageChange(e.target.value)}
                aria-label="Select Interface Language"
              >
                {LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.label}
                  </option>
                ))}
              </select>
              <span className="lang-chevron" aria-hidden="true">▼</span>
            </div>

            {/* Profile Button */}
            <button
              type="button"
              className="header-action-btn"
              onClick={() => setShowProfileModal(true)}
              aria-label={t("profileNav", selectedLang)}
            >
              <span>👤</span>
              <span>{t("profileNav", selectedLang)}</span>
            </button>

            {/* Logout Button */}
            <button
              type="button"
              className="header-logout-btn"
              onClick={handleLogout}
              aria-label={t("logout", selectedLang)}
            >
              {t("logout", selectedLang)}
            </button>
          </div>
        </div>
      </header>

      {/* MAIN VIEW CONTENT CONTAINER */}
      <main className="main-content">
        {/* VIEW 1: DEDICATED VOICE SCREEN */}
        {activeView === "voice" && (
          <div className="section-block">
            <button
              type="button"
              className="header-action-btn"
              style={{ width: "fit-content", marginBottom: "8px" }}
              onClick={() => setActiveView("home")}
            >
              ← {t("back", selectedLang)}
            </button>
            <VoiceAssistant
              selectedLang={selectedLang}
              userState={userState}
              userProfile={profile}
              userGPSCoords={userGPSCoords}
              onNavigateToHospitals={() => handleOpenHospitals()}
            />
          </div>
        )}

        {/* VIEW 1B: AI HEALTH IMAGE ASSISTANT */}
        {activeView === "image" && (
          <div className="section-block">
            <button
              type="button"
              className="header-action-btn"
              style={{ width: "fit-content", marginBottom: "8px" }}
              onClick={() => setActiveView("home")}
            >
              ← {t("back", selectedLang)}
            </button>
            <ImageAssistant
              currentLang={selectedLang}
              userProfile={profile}
              onNavigateToHospitals={() => handleOpenHospitals()}
            />
          </div>
        )}

        {/* VIEW 2: DEDICATED HEALTH GUIDANCE (Symptom Guides) */}
        {activeView === "guidance" && (
          <div className="section-block">
            <button
              type="button"
              className="header-action-btn"
              style={{ width: "fit-content", marginBottom: "8px" }}
              onClick={() => setActiveView("home")}
            >
              ← {t("back", selectedLang)}
            </button>
            <div className="section-header">
              <div>
                <h1 className="section-title">{t("healthGuidanceTitle", selectedLang)}</h1>
                <p className="hero-tagline" style={{ fontSize: "0.88rem" }}>
                  {t("healthGuidanceDesc", selectedLang)}
                </p>
              </div>
            </div>

            <div className="guidance-cards-grid">
              {HEALTH_GUIDANCE_ITEMS.map((item) => (
                <div key={item.id} className="guidance-card">
                  <h3 className="guidance-card-title">
                    {item.title[selectedLang] || item.title["en-IN"]}
                  </h3>
                  <p className="guidance-card-desc">
                    {item.indicates[selectedLang] || item.indicates["en-IN"]}
                  </p>

                  <div className="guidance-section-block">
                    <span className="guidance-block-label">{t("safeSelfCareSteps", selectedLang)}:</span>
                    <ul className="guidance-bullet-list">
                      {(item.safeCare[selectedLang] || item.safeCare["en-IN"] || []).map((step, idx) => (
                        <li key={idx}>{step}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="guidance-section-block warning">
                    <span className="guidance-block-label" style={{ color: "var(--emergency-color)" }}>{t("whenToSeeDoctor", selectedLang)}:</span>
                    <ul className="guidance-bullet-list">
                      {(item.warningSigns[selectedLang] || item.warningSigns["en-IN"] || []).map((w, idx) => (
                        <li key={idx}>{w}</li>
                      ))}
                    </ul>
                  </div>

                  <div style={{ display: "flex", gap: "8px", marginTop: "14px", flexWrap: "wrap" }}>
                    <button
                      type="button"
                      className="btn-primary-auth"
                      style={{ width: "auto", padding: "8px 14px", fontSize: "0.82rem" }}
                      onClick={() => setActiveView("voice")}
                    >
                      💬 {t("askArogyaAboutThis", selectedLang)}
                    </button>
                    <button
                      type="button"
                      className="header-action-btn"
                      style={{ padding: "8px 14px", fontSize: "0.82rem" }}
                      onClick={() => handleOpenHospitals()}
                    >
                      🏥 {t("hospitalsNav", selectedLang)}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* VIEW 3: DEDICATED NEARBY HOSPITALS (Tamil Nadu Registry & GPS) */}
        {activeView === "hospitals" && (
          <div className="section-block">
            <button
              type="button"
              className="header-action-btn"
              style={{ width: "fit-content", marginBottom: "8px" }}
              onClick={() => setActiveView("home")}
            >
              ← {t("back", selectedLang)}
            </button>

            <div className="section-header">
              <div>
                <h1 className="section-title">{t("nearbyHospitalsTitle", selectedLang)}</h1>
                <p className="hero-tagline" style={{ fontSize: "0.88rem" }}>
                  {t("nearbyHospitalsDesc", selectedLang)}
                </p>
              </div>
            </div>

            {/* Location Permission & Priority Selector */}
            <LocationPermissionCard
              currentLocationType={gpsLocationActive ? "gps" : (userHierarchyLocation.district === profile?.district ? "profile" : "manual")}
              activeLocationLabel={userLocationMeta?.label || (gpsLocationActive ? "Current GPS Position" : `${userHierarchyLocation.locality ? `${userHierarchyLocation.locality}, ` : ""}${userHierarchyLocation.district || selectedDistrict}, ${userHierarchyLocation.state || "Tamil Nadu"}`)}
              coordinates={{
                latitude: userLocationMeta?.latitude || userGPSCoords?.latitude || profile?.latitude,
                longitude: userLocationMeta?.longitude || userGPSCoords?.longitude || profile?.longitude,
              }}
              selectedState={userHierarchyLocation.state}
              selectedDistrict={userHierarchyLocation.district}
              selectedTaluk={userHierarchyLocation.taluk}
              selectedLocality={userHierarchyLocation.locality}
              selectedPincode={userHierarchyLocation.pincode}
              searchRadiusKm={searchRadiusKm}
              onLocationChange={(loc) => {
                setUserHierarchyLocation({
                  state: loc.state,
                  district: loc.district,
                  taluk: loc.taluk,
                  locality: loc.locality,
                  pincode: loc.pincode,
                });
                setSelectedDistrict(loc.district);
                setGpsLocationActive(loc.type === "gps");
                if (loc.type !== "gps") setUserGPSCoords(null);
                fetchNearbyHospitals({
                  lat: loc.latitude,
                  lon: loc.longitude,
                  state: loc.state,
                  district: loc.district,
                  taluk: loc.taluk,
                  locality: loc.locality,
                  pincode: loc.pincode,
                  radius_km: searchRadiusKm,
                });
              }}
              onRadiusChange={(rad) => {
                setSearchRadiusKm(rad);
                fetchNearbyHospitals({ radius_km: rad });
              }}
              onRequestGPS={handleRequestGPSLocation}
              onSearchAgain={() => fetchNearbyHospitals({ radius_km: searchRadiusKm })}
              isBusy={hospitalsLoading}
              languageCode={selectedLang}
              permissionNotice={locationPermissionNotice}
            />

            {hospitalsError && (
              <div className="auth-error-banner" style={{ marginTop: "12px" }}>
                <span>⚠️</span>
                <span>{hospitalsError}</span>
              </div>
            )}

            {hospitalsLoading ? (
              <div style={{ padding: "40px", textAlign: "center", color: "var(--text-secondary)" }}>
                <span className="spinner-dot" style={{ display: "inline-block", marginRight: "8px" }} />
                {t("findingHospitals", selectedLang)}
              </div>
            ) : hospitals.length === 0 ? (
              <div className="empty-hospitals-box" style={{ padding: "40px 20px", textAlign: "center", background: "var(--bg-card)", borderRadius: "var(--radius-lg)", border: "1px solid var(--border-color)", marginTop: "16px" }}>
                <div style={{ fontSize: "2.4rem", marginBottom: "10px" }}>🏥</div>
                <h3 style={{ fontSize: "1.15rem", marginBottom: "8px", color: "var(--text-primary)" }}>
                  {t("noHospitalsInRadius", selectedLang)}
                </h3>
                <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", marginBottom: "18px", maxWidth: "480px", margin: "0 auto 18px" }}>
                  No verified hospitals found within <strong>{searchRadiusKm} km</strong> of {userLocationMeta?.label || userHierarchyLocation.district || selectedDistrict}.
                </p>
                <button
                  type="button"
                  className="btn-primary-auth"
                  style={{ width: "auto", padding: "10px 28px", margin: "0 auto" }}
                  onClick={() => {
                    const next = searchRadiusKm < 25 ? 25 : 50;
                    setSearchRadiusKm(next);
                    fetchNearbyHospitals({ radius_km: next });
                  }}
                >
                  🎯 {t("expandRadius", selectedLang)} ({searchRadiusKm < 25 ? "25 km" : "50 km"})
                </button>
              </div>
            ) : (
              <div className="hospitals-map-layout">
                {/* Desktop: Map on Left (55%) | Mobile: Map on Top */}
                <div className="hospitals-map-pane">
                  <HospitalMap
                    hospitals={hospitals}
                    userLocation={userLocationMeta}
                    selectedHospital={selectedHospitalDetail}
                    onSelectHospital={(hosp) => {
                      setSelectedHospitalDetail((prev) => (prev?.id === hosp?.id ? null : hosp));
                    }}
                    height="480px"
                    languageCode={selectedLang}
                  />
                </div>

                {/* Desktop: Hospital List on Right (45%) | Mobile: List Below */}
                <div className="hospitals-list-pane">
                  <div className="hospitals-grid-stacked">
                    {hospitals.map((hosp) => {
                      const isSelected = selectedHospitalDetail?.id === hosp.id;
                      return (
                        <article
                          key={hosp.id}
                          className={`hospital-card ${isSelected ? "selected-hospital" : ""}`}
                          onClick={() => setSelectedHospitalDetail(isSelected ? null : hosp)}
                        >
                          <div className="hospital-header">
                            <span className="badge-state">{hosp.type}</span>
                            {hosp.distance_label && (
                              <span className="badge-distance">
                                {hosp.distance_label}
                              </span>
                            )}
                          </div>

                          <h3 className="hospital-name">{hosp.name}</h3>
                          <p className="hospital-address">{hosp.address}</p>

                          <div className="hospital-status-pill">
                            <span>🟢</span>
                            <span>{hosp.open_status || t("emergencyServices", selectedLang)}</span>
                          </div>

                          {/* INLINE EXPANDED DETAILS (Replaces broken modal overlay) */}
                          {isSelected && (
                            <div className="hospital-inline-details" onClick={(e) => e.stopPropagation()}>
                              {hosp.services && hosp.services.length > 0 && (
                                <div className="inline-detail-block">
                                  <h4 className="inline-detail-title">Departments & Facilities</h4>
                                  <div className="inline-pills-row">
                                    {hosp.services.map((srv, idx) => (
                                      <span key={idx} className="profile-meta-pill">✓ {srv}</span>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {hosp.schemes_accepted && hosp.schemes_accepted.length > 0 && (
                                <div className="inline-detail-block">
                                  <h4 className="inline-detail-title">Empanelled Schemes</h4>
                                  <div className="inline-pills-row">
                                    {hosp.schemes_accepted.map((sch, idx) => (
                                      <span key={idx} className="badge-state">{sch}</span>
                                    ))}
                                  </div>
                                </div>
                              )}

                              <div className="inline-helpline-box">
                                📞 <strong>Emergency Helpline:</strong> {hosp.phone || "108"} (24/7 Available)
                              </div>
                            </div>
                          )}

                          <div className="hospital-card-actions">
                            <a
                              href={hosp.maps_url || hosp.directions_url}
                              target="_blank"
                              rel="noreferrer"
                              className="btn-hospital-directions"
                              onClick={(e) => e.stopPropagation()}
                            >
                              🗺️ {t("getDirections", selectedLang)}
                            </a>
                            {hosp.phone && (
                              <a
                                href={`tel:${hosp.phone}`}
                                className="btn-hospital-call"
                                onClick={(e) => e.stopPropagation()}
                              >
                                📞 {t("callHospital", selectedLang)}
                              </a>
                            )}
                            <button
                              type="button"
                              className="btn-hospital-detail"
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedHospitalDetail(isSelected ? null : hosp);
                              }}
                            >
                              {isSelected ? "▲ Less Details" : t("viewDetails", selectedLang)}
                            </button>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* VIEW 4: DEDICATED SCHEME DIRECTORY */}
        {activeView === "schemes" && (
          <div className="section-block">
            <button
              type="button"
              className="header-action-btn"
              style={{ width: "fit-content", marginBottom: "8px" }}
              onClick={() => setActiveView("home")}
            >
              ← {t("back", selectedLang)}
            </button>
            <div className="section-header">
              <h1 className="section-title">{t("govtSchemes", selectedLang)}</h1>
            </div>
            <div className="schemes-grid">
              {recommendedCards.map((scheme) => {
                const name = getSchemeTitle(scheme.scheme_name, scheme.scheme_id);
                const desc = scheme.short_description?.[selectedLang.slice(0, 2)] || scheme.short_description?.en || "";
                const status = scheme.eligibility_status || "Likely Eligible";

                return (
                  <article key={scheme.scheme_id} className="scheme-card">
                    <div>
                      <div className="scheme-badges-row">
                        <span className="badge-state">{getLocalizedState(scheme.state || "National", selectedLang)}</span>
                        <span className={`badge-status ${status.toLowerCase().includes("likely") ? "likely" : status.toLowerCase().includes("possibly") ? "possibly" : "info-needed"}`}>
                          {getLocalizedStatus(status, selectedLang)}
                        </span>
                      </div>
                      <h3 className="scheme-card-title">{name}</h3>
                      <p className="scheme-card-desc">{desc}</p>
                    </div>

                    <div className="scheme-card-footer">
                      <span className="scheme-source-text">
                        {scheme.official_source || "National Health Mission"}
                      </span>
                      <button
                        type="button"
                        className="btn-view-details"
                        onClick={() => setSelectedScheme(scheme)}
                      >
                        {t("viewDetails", selectedLang)} →
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        )}

        {/* VIEW 5: DEDICATED SCHEME COMPARISON */}
        {activeView === "compare" && (
          <div className="section-block">
            <button
              type="button"
              className="header-action-btn"
              style={{ width: "fit-content", marginBottom: "8px" }}
              onClick={() => setActiveView("home")}
            >
              ← {t("back", selectedLang)}
            </button>
            <SchemeComparison languageCode={selectedLang} />
          </div>
        )}

        {/* VIEW 6: DEDICATED ELIGIBILITY REPORT (NEVER BLANK) */}
        {activeView === "eligibility" && (
          <div className="section-block">
            <button
              type="button"
              className="header-action-btn"
              style={{ width: "fit-content", marginBottom: "8px" }}
              onClick={() => setActiveView("home")}
            >
              ← {t("back", selectedLang)}
            </button>

            <div className="section-header">
              <div>
                <h1 className="section-title">{t("eligibilityReportTitle", selectedLang)}</h1>
                <p className="hero-tagline" style={{ fontSize: "0.9rem" }}>
                  {t("eligibilityReportDesc", selectedLang)}
                </p>
              </div>
              <button
                type="button"
                className="btn-primary-auth"
                style={{ width: "auto", padding: "8px 18px", fontSize: "0.85rem" }}
                onClick={() => setShowProfileModal(true)}
              >
                ✏️ {t("editProfile", selectedLang)}
              </button>
            </div>

            {/* Incomplete profile warning */}
            {profileCompletion < 40 && (
              <div className="incomplete-profile-banner">
                <div>
                  <strong>{t("incompleteProfileNotice", selectedLang)}</strong>
                  <div style={{ fontSize: "0.85rem", opacity: 0.9 }}>
                    Current profile completion: {profileCompletion}%. Adding state, income, and demographic status produces high-confidence scheme evaluations.
                  </div>
                </div>
                <button
                  type="button"
                  className="btn-primary-auth"
                  style={{ width: "auto", padding: "6px 14px", fontSize: "0.82rem", whiteSpace: "nowrap" }}
                  onClick={() => setShowProfileModal(true)}
                >
                  {t("completeProfileNow", selectedLang)}
                </button>
              </div>
            )}

            {eligibilityError && (
              <div className="auth-error-banner" style={{ marginBottom: "16px" }}>
                <span>⚠️</span>
                <span>{eligibilityError}</span>
              </div>
            )}

            {eligibilityLoading ? (
              <div style={{ padding: "48px 24px", textAlign: "center", color: "var(--text-secondary)" }}>
                <div style={{ fontSize: "1.8rem", marginBottom: "10px" }}>⏳</div>
                <div>{t("evaluatingEligibility", selectedLang)}</div>
              </div>
            ) : !eligibilityData?.schemes || eligibilityData.schemes.length === 0 ? (
              <div style={{ padding: "40px", textAlign: "center", color: "var(--text-secondary)" }}>
                <p>{t("evaluateProfilePrompt", selectedLang)}</p>
                <button
                  type="button"
                  className="btn-primary-auth"
                  style={{ margin: "16px auto 0", width: "auto" }}
                  onClick={handleRunEligibility}
                >
                  {t("assessEligibilityNow", selectedLang)}
                </button>
              </div>
            ) : (
              <div className="eligibility-sections-wrap">
                {/* 1. Likely Eligible Section */}
                {categorizedEligibility.likely.length > 0 && (
                  <div className="eligibility-group">
                    <h2 className="eligibility-group-title green">
                      <span>✓</span> {t("eligibleCategory", selectedLang)} ({categorizedEligibility.likely.length})
                    </h2>
                    <div className="schemes-grid">
                      {categorizedEligibility.likely.map((item, idx) => {
                        const title = getSchemeTitle(item.scheme_name, item.scheme_id);
                        return (
                          <article key={idx} className="scheme-card eligibility-item-card">
                            <div>
                              <div className="scheme-badges-row">
                                <span className="badge-state">{getLocalizedState(item.state || "National", selectedLang)}</span>
                                <span className="badge-status likely">
                                  {getLocalizedStatus(item.eligibility_status, selectedLang)}
                                </span>
                              </div>
                              <h3 className="scheme-card-title">{title}</h3>
                              {item.possible_reason && (
                                <p className="scheme-card-desc">{item.possible_reason}</p>
                              )}

                              {item.matched_criteria && item.matched_criteria.length > 0 && (
                                <div className="criteria-checklist">
                                  <span className="criteria-label">✓ {t("whyYouMatch", selectedLang)}:</span>
                                  <ul>
                                    {item.matched_criteria.map((c, cIdx) => (
                                      <li key={cIdx}>{c}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>

                            <div className="scheme-card-footer">
                              <span className="scheme-source-text">
                                {item.official_source || "Official Portal"}
                              </span>
                              {item.official_url && (
                                <a
                                  href={item.official_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="btn-view-details"
                                >
                                  Portal ↗
                                </a>
                              )}
                            </div>
                          </article>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* 2. Potentially Eligible Section */}
                {categorizedEligibility.possible.length > 0 && (
                  <div className="eligibility-group">
                    <h2 className="eligibility-group-title amber">
                      <span>ℹ️</span> {t("potentiallyEligibleCategory", selectedLang)} ({categorizedEligibility.possible.length})
                    </h2>
                    <div className="schemes-grid">
                      {categorizedEligibility.possible.map((item, idx) => {
                        const title = getSchemeTitle(item.scheme_name, item.scheme_id);
                        return (
                          <article key={idx} className="scheme-card eligibility-item-card">
                            <div>
                              <div className="scheme-badges-row">
                                <span className="badge-state">{getLocalizedState(item.state || "National", selectedLang)}</span>
                                <span className="badge-status possibly">
                                  {getLocalizedStatus(item.eligibility_status, selectedLang)}
                                </span>
                              </div>
                              <h3 className="scheme-card-title">{title}</h3>
                              {item.possible_reason && (
                                <p className="scheme-card-desc">{item.possible_reason}</p>
                              )}

                              {item.missing_information && item.missing_information.length > 0 && (
                                <div className="criteria-checklist info">
                                  <span className="criteria-label" style={{ color: "#93c5fd" }}>• {t("missingInfo", selectedLang)}:</span>
                                  <ul>
                                    {item.missing_information.map((m, mIdx) => (
                                      <li key={mIdx}>{m}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>

                            <div className="scheme-card-footer">
                              <span className="scheme-source-text">
                                {item.official_source || "Official Portal"}
                              </span>
                              {item.official_url && (
                                <a
                                  href={item.official_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="btn-view-details"
                                >
                                  Portal ↗
                                </a>
                              )}
                            </div>
                          </article>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* 3. More Information Needed Section */}
                {categorizedEligibility.infoNeeded.length > 0 && (
                  <div className="eligibility-group">
                    <h2 className="eligibility-group-title">
                      <span>❓</span> {t("infoNeededCategory", selectedLang)} ({categorizedEligibility.infoNeeded.length})
                    </h2>
                    <div className="schemes-grid">
                      {categorizedEligibility.infoNeeded.map((item, idx) => {
                        const title = getSchemeTitle(item.scheme_name, item.scheme_id);
                        return (
                          <article key={idx} className="scheme-card eligibility-item-card">
                            <div>
                              <div className="scheme-badges-row">
                                <span className="badge-state">{getLocalizedState(item.state || "National", selectedLang)}</span>
                                <span className="badge-status info-needed">
                                  {getLocalizedStatus(item.eligibility_status, selectedLang)}
                                </span>
                              </div>
                              <h3 className="scheme-card-title">{title}</h3>
                              {item.possible_reason && (
                                <p className="scheme-card-desc">{item.possible_reason}</p>
                              )}

                              {item.missing_information && item.missing_information.length > 0 && (
                                <div className="criteria-checklist info">
                                  <span className="criteria-label" style={{ color: "#93c5fd" }}>• {t("missingInfo", selectedLang)}:</span>
                                  <ul>
                                    {item.missing_information.map((m, mIdx) => (
                                      <li key={mIdx}>{m}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>

                            <div className="scheme-card-footer">
                              <span className="scheme-source-text">
                                {item.official_source || "Official Portal"}
                              </span>
                              {item.official_url && (
                                <a
                                  href={item.official_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="btn-view-details"
                                >
                                  Portal ↗
                                </a>
                              )}
                            </div>
                          </article>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* VIEW 7: PRIMARY HOME DASHBOARD (Standard View) */}
        {activeView === "home" && (
          <>
            {/* 1. Welcome / Hero Section */}
            <section className="hero-section">
              <span className="hero-eyebrow">
                {getGreeting(selectedLang)}, {authUser?.name || "Patient"}
              </span>
              <h1 className="hero-heading">
                AROGYA NEXUS
              </h1>
              <p className="hero-tagline">
                {t("welcomeTagline", selectedLang)}
              </p>
            </section>

            {/* 2. Primary Navigation Cards (Simple, clear 5 pathways) */}
            <section className="section-block" aria-label="Care Pathways">
              <div className="quick-actions-grid">
                {/* 1. Talk to Arogya */}
                <button
                  type="button"
                  className="quick-action-card"
                  onClick={() => setActiveView("voice")}
                >
                  <div className="action-icon-box">
                    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                      <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
                    </svg>
                  </div>
                  <div className="action-text-box">
                    <span className="action-title">{t("arogya", selectedLang)}</span>
                    <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>Symptom & Voice Care</span>
                  </div>
                  <span className="action-arrow">→</span>
                </button>

                {/* 1B. AI Health Photo Assistant */}
                <button
                  type="button"
                  className="quick-action-card"
                  onClick={() => setActiveView("image")}
                >
                  <div className="action-icon-box">
                    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                      <circle cx="12" cy="13" r="4" />
                    </svg>
                  </div>
                  <div className="action-text-box">
                    <span className="action-title">{t("imageNav", selectedLang)}</span>
                    <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>Visual Wound & Skin Care</span>
                  </div>
                  <span className="action-arrow">→</span>
                </button>

                {/* 2. Health Guidance */}
                <button
                  type="button"
                  className="quick-action-card"
                  onClick={() => setActiveView("guidance")}
                >
                  <div className="action-icon-box">
                    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                    </svg>
                  </div>
                  <div className="action-text-box">
                    <span className="action-title">{t("guidanceNav", selectedLang)}</span>
                    <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>Safe Home Self-Care</span>
                  </div>
                  <span className="action-arrow">→</span>
                </button>

                {/* 3. Nearby Hospitals */}
                <button
                  type="button"
                  className="quick-action-card"
                  onClick={() => handleOpenHospitals()}
                >
                  <div className="action-icon-box">
                    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 2a8 8 0 0 0-8 8c0 5.25 8 12 8 12s8-6.75 8-12a8 8 0 0 0-8-8z" />
                      <circle cx="12" cy="10" r="3" />
                    </svg>
                  </div>
                  <div className="action-text-box">
                    <span className="action-title">{t("hospitalsNav", selectedLang)}</span>
                    <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>Government Centers & 24/7</span>
                  </div>
                  <span className="action-arrow">→</span>
                </button>

                {/* 4. Government Schemes */}
                <button
                  type="button"
                  className="quick-action-card"
                  onClick={() => setActiveView("schemes")}
                >
                  <div className="action-icon-box">
                    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="3" y="3" width="18" height="18" rx="2" />
                      <path d="M3 9h18M9 21V9" />
                    </svg>
                  </div>
                  <div className="action-text-box">
                    <span className="action-title">{t("govtSchemes", selectedLang)}</span>
                    <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>CMCHIS, PM-JAY, KASP</span>
                  </div>
                  <span className="action-arrow">→</span>
                </button>

                {/* 5. My Eligibility */}
                <button
                  type="button"
                  className="quick-action-card"
                  onClick={handleRunEligibility}
                >
                  <div className="action-icon-box">
                    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" />
                      <path d="m9 12 2 2 4-4" />
                    </svg>
                  </div>
                  <div className="action-text-box">
                    <span className="action-title">{t("myEligibility", selectedLang)}</span>
                    <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>{profileCompletion}% complete</span>
                  </div>
                  <span className="action-arrow">→</span>
                </button>

                {/* 6. Emergency 108 */}
                <a
                  href="tel:108"
                  className="quick-action-card emergency-accent"
                >
                  <div className="action-icon-box">
                    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
                    </svg>
                  </div>
                  <div className="action-text-box">
                    <span className="action-title" style={{ color: "#fca5a5" }}>{t("emergencyCall108", selectedLang)}</span>
                    <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>Instant Ambulance</span>
                  </div>
                  <span className="action-arrow">→</span>
                </a>
              </div>
            </section>

            {/* 3. Health Profile Summary Card */}
            <section aria-label={t("healthProfile", selectedLang)}>
              <div className="profile-summary-card">
                <div className="profile-card-top">
                  <div className="profile-headline">
                    <h2 className="section-title">{t("healthProfile", selectedLang)}</h2>
                    <span className="profile-completion-badge">
                      {profileCompletion}% {t("profileCompletion", selectedLang)}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="btn-primary-auth"
                    style={{ width: "auto", padding: "8px 18px", fontSize: "0.85rem" }}
                    onClick={() => setShowProfileModal(true)}
                  >
                    ✏️ {t("editProfile", selectedLang)}
                  </button>
                </div>

                <div className="profile-meta-row">
                  <span className="profile-meta-pill">
                    📍 {getLocalizedState(profile.state || "Tamil Nadu", selectedLang)} • {profile.district || "Salem"}
                  </span>
                  <span className="profile-meta-pill">
                    👤 {t("ageLabel", selectedLang)}: {profile.age || "19"} • {profile.gender ? t(`gender${profile.gender.charAt(0).toUpperCase()}${profile.gender.slice(1)}`, selectedLang) : t("notSpecified", selectedLang)}
                  </span>
                  <span className="profile-meta-pill">
                    💰 {profile.income_range || "< 1.2L"}
                  </span>
                </div>

                {/* Presets Row */}
                <div className="preset-bar">
                  <span className="preset-title">{t("profileQuickPresets", selectedLang)}:</span>
                  <button
                    type="button"
                    className="preset-pill-btn"
                    onClick={() => applyPresetFromHome("pregnancy")}
                  >
                    {t("presetPregnancy", selectedLang)}
                  </button>
                  <button
                    type="button"
                    className="preset-pill-btn"
                    onClick={() => applyPresetFromHome("low_income")}
                  >
                    {t("presetLowIncome", selectedLang)}
                  </button>
                  <button
                    type="button"
                    className="preset-pill-btn"
                    onClick={() => applyPresetFromHome("senior")}
                  >
                    {t("presetSeniorCitizen", selectedLang)}
                  </button>
                  <button
                    type="button"
                    className="preset-pill-btn"
                    onClick={() => applyPresetFromHome("pensioner")}
                  >
                    {t("presetPensioner", selectedLang)}
                  </button>
                </div>
              </div>
            </section>

            {/* 4. Recommended Schemes Section */}
            <section className="section-block" aria-label={t("recommendedSchemes", selectedLang)}>
              <div className="section-header">
                <div>
                  <h2 className="section-title">{t("recommendedSchemes", selectedLang)}</h2>
                  <p className="hero-tagline" style={{ fontSize: "0.88rem" }}>
                    {t("healthCoverage", selectedLang)}
                  </p>
                </div>
                <button
                  type="button"
                  className="header-action-btn"
                  onClick={() => setActiveView("schemes")}
                >
                  {t("viewDetails", selectedLang)} →
                </button>
              </div>

              {schemesLoading ? (
                <div style={{ padding: "32px", textAlign: "center", color: "var(--text-secondary)" }}>
                  Loading personalized scheme recommendations...
                </div>
              ) : (
                <div className="schemes-grid">
                  {recommendedCards.map((scheme) => {
                    const name = getSchemeTitle(scheme.scheme_name, scheme.scheme_id);
                    const desc = scheme.short_description?.[selectedLang.slice(0, 2)] || scheme.short_description?.en || "";
                    const status = scheme.eligibility_status || "Likely Eligible";

                    return (
                      <article key={scheme.scheme_id} className="scheme-card">
                        <div>
                          <div className="scheme-badges-row">
                            <span className="badge-state">{getLocalizedState(scheme.state || "National", selectedLang)}</span>
                            <span className={`badge-status ${status.toLowerCase().includes("likely") ? "likely" : status.toLowerCase().includes("possibly") ? "possibly" : "info-needed"}`}>
                              {getLocalizedStatus(status, selectedLang)}
                            </span>
                          </div>
                          <h3 className="scheme-card-title">{name}</h3>
                          <p className="scheme-card-desc">{desc}</p>
                        </div>

                        <div className="scheme-card-footer">
                          <span className="scheme-source-text">
                            {scheme.official_source || "Official Health Mission"}
                          </span>
                          <button
                            type="button"
                            className="btn-view-details"
                            onClick={() => setSelectedScheme(scheme)}
                          >
                            {t("viewDetails", selectedLang)} →
                          </button>
                        </div>
                      </article>
                    );
                  })}
                </div>
              )}
            </section>

            {/* 5. Emergency Help Section */}
            <section aria-label="Emergency Help">
              <div className="emergency-card">
                <div className="emergency-info-box">
                  <h2 className="emergency-title">
                    <span>🚨</span>
                    <span>{t("emergencyAlertTitle", selectedLang)}</span>
                  </h2>
                  <p className="emergency-desc">
                    {t("emergencyAlertDesc", selectedLang)}
                  </p>
                </div>

                <div className="emergency-btn-group">
                  <a href="tel:108" className="btn-emergency-call">
                    📞 {t("emergencyCall108", selectedLang)}
                  </a>
                  <a href="tel:104" className="btn-helpline">
                    ℹ️ {t("emergencyHelpline104", selectedLang)}
                  </a>
                </div>
              </div>
            </section>
          </>
        )}
      </main>

      {/* Mobile Bottom Navigation Bar (5 core routes) */}
      <nav className="mobile-bottom-nav" aria-label="Mobile Navigation">
        <button
          type="button"
          className={`mobile-nav-item ${activeView === "home" ? "active" : ""}`}
          onClick={() => setActiveView("home")}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
          </svg>
          <span>{t("home", selectedLang)}</span>
        </button>

        <button
          type="button"
          className={`mobile-nav-item ${activeView === "voice" ? "active" : ""}`}
          onClick={() => setActiveView("voice")}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
            <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
          </svg>
          <span>Arogya</span>
        </button>

        <button
          type="button"
          className={`mobile-nav-item ${activeView === "image" ? "active" : ""}`}
          onClick={() => setActiveView("image")}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
            <circle cx="12" cy="13" r="4" />
          </svg>
          <span>{t("imageNav", selectedLang)}</span>
        </button>

        <button
          type="button"
          className={`mobile-nav-item ${activeView === "guidance" ? "active" : ""}`}
          onClick={() => setActiveView("guidance")}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
          </svg>
          <span>Guidance</span>
        </button>

        <button
          type="button"
          className={`mobile-nav-item ${activeView === "hospitals" ? "active" : ""}`}
          onClick={() => handleOpenHospitals()}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2a8 8 0 0 0-8 8c0 5.25 8 12 8 12s8-6.75 8-12a8 8 0 0 0-8-8z" />
            <circle cx="12" cy="10" r="3" />
          </svg>
          <span>Hospitals</span>
        </button>

        <button
          type="button"
          className={`mobile-nav-item ${activeView === "schemes" ? "active" : ""}`}
          onClick={() => setActiveView("schemes")}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M3 9h18M9 21V9" />
          </svg>
          <span>Schemes</span>
        </button>
      </nav>

      {/* MODAL 1: Health Profile 4-Step Stepper */}
      {showProfileModal && (
        <HealthProfile
          isModal
          onClose={() => setShowProfileModal(false)}
          onProfileChange={handleProfileUpdate}
          languageCode={selectedLang}
          userState={userState}
        />
      )}

      {/* MODAL 2: Scheme Details Modal */}
      {selectedScheme && (
        <div className="modal-overlay" onClick={() => setSelectedScheme(null)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <span className="badge-state" style={{ marginBottom: "4px", display: "inline-block" }}>
                  {getLocalizedState(selectedScheme.state || "National", selectedLang)}
                </span>
                <h3 className="modal-title">
                  {getSchemeTitle(selectedScheme.scheme_name, selectedScheme.scheme_id)}
                </h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setSelectedScheme(null)}
                aria-label={t("close", selectedLang)}
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              <div>
                <h4 style={{ fontSize: "0.95rem", color: "var(--accent-primary)", marginBottom: "6px" }}>
                  {t("benefits", selectedLang)}
                </h4>
                <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)", lineHeight: "1.6" }}>
                  {selectedScheme.short_description?.[selectedLang.slice(0, 2)] || selectedScheme.short_description?.en || selectedScheme.benefits?.en?.[0] || t("healthCoverage", selectedLang)}
                </p>
              </div>

              <div>
                <h4 style={{ fontSize: "0.95rem", color: "var(--accent-primary)", marginBottom: "6px" }}>
                  {t("eligibilityCriteria", selectedLang)}
                </h4>
                <ul style={{ paddingLeft: "20px", fontSize: "0.9rem", color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: "6px" }}>
                  {(selectedScheme.eligibility?.en || [selectedScheme.target_beneficiaries?.en || "Eligible citizens per annual income criteria."]).map((crit, idx) => (
                    <li key={idx}>{crit}</li>
                  ))}
                </ul>
              </div>

              <div>
                <h4 style={{ fontSize: "0.95rem", color: "var(--accent-primary)", marginBottom: "6px" }}>
                  {t("requiredDocuments", selectedLang)}
                </h4>
                <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)" }}>
                  Aadhaar Card, Ration Card (Smart card / BPL), Income Certificate from local revenue authority.
                </p>
              </div>

              <div style={{ padding: "12px", background: "var(--bg-card)", borderRadius: "var(--radius-md)", fontSize: "0.82rem", color: "var(--text-muted)" }}>
                ℹ️ {t("officialConfirmationNote", selectedLang)}
              </div>
            </div>

            <div className="modal-footer">
              {selectedScheme.official_url && (
                <a
                  href={selectedScheme.official_url}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-primary-auth"
                  style={{ width: "auto", padding: "8px 20px" }}
                >
                  Official Portal ↗
                </a>
              )}
              <button
                type="button"
                className="header-action-btn"
                onClick={() => setSelectedScheme(null)}
              >
                {t("close", selectedLang)}
              </button>
            </div>
          </div>
        </div>
      )}


    </div>
  );
}

export default App;
