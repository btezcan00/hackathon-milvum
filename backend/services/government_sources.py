"""
Dutch Government Websites and Pages Configuration

This module contains a curated list of Dutch government websites and specific pages
that can be crawled for information retrieval. Each entry includes:
- url: The URL to crawl
- title: A short title describing the page
- description: A description of what information this page contains
- category: The category/domain of government service (e.g., 'immigration', 'taxes', 'education')
"""

GOVERNMENT_SOURCES = [
    # Main Government Portal
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen",
        "title": "Rijksoverheid - Alle Onderwerpen",
        "description": "Comprehensive directory of all government topics and services",
        "category": "general"
    },
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/werknemersverzekeringen",
        "title": "Werknemersverzekeringen",
        "description": "Information about employee insurance schemes in the Netherlands",
        "category": "employment"
    },
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/belastingen",
        "title": "Belastingen",
        "description": "Tax information, filing requirements, and tax services",
        "category": "taxes"
    },
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/reizen-en-verblijf-in-het-buitenland",
        "title": "Reizen en Verblijf in het Buitenland",
        "description": "Travel abroad, passports, visas, and consular services",
        "category": "travel"
    },
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/immigratie-en-nationaliteit",
        "title": "Immigratie en Nationaliteit",
        "description": "Immigration, naturalization, residence permits, and citizenship",
        "category": "immigration"
    },
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/onderwijs",
        "title": "Onderwijs",
        "description": "Education system, schools, student finance, and educational policies",
        "category": "education"
    },
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/zorgverzekering",
        "title": "Zorgverzekering",
        "description": "Health insurance requirements, coverage, and healthcare system",
        "category": "healthcare"
    },
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/werk-en-bijstand",
        "title": "Werk en Bijstand",
        "description": "Unemployment benefits, social assistance, and job search support",
        "category": "employment"
    },
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/pensioen",
        "title": "Pensioen",
        "description": "Pension system, retirement benefits, and pension planning",
        "category": "pensions"
    },
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/digid",
        "title": "DigiD",
        "description": "Digital identity system for accessing government services online",
        "category": "digital_services"
    },
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/rijbewijs",
        "title": "Rijbewijs",
        "description": "Driver's license, driving tests, and traffic regulations",
        "category": "transportation"
    },
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/huisvesting",
        "title": "Huisvesting",
        "description": "Housing, rent, mortgage, and housing benefits",
        "category": "housing"
    },
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/gezinsbijslag",
        "title": "Gezinsbijslag",
        "description": "Child benefits and family allowances",
        "category": "family"
    },
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/milieu-en-natuur",
        "title": "Milieu en Natuur",
        "description": "Environmental policies, sustainability, and nature conservation",
        "category": "environment"
    },
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/veiligheid",
        "title": "Veiligheid",
        "description": "Public safety, emergency services, and security measures",
        "category": "safety"
    },
    
    # IND (Immigration and Naturalization Service)
    {
        "url": "https://ind.nl/werk",
        "title": "IND - Werken in Nederland",
        "description": "Work permits, residence permits for work, and employment-based immigration",
        "category": "immigration"
    },
    {
        "url": "https://ind.nl/studie",
        "title": "IND - Studeren in Nederland",
        "description": "Student residence permits and studying in the Netherlands",
        "category": "immigration"
    },
    {
        "url": "https://ind.nl/gezin",
        "title": "IND - Gezinshereniging",
        "description": "Family reunification and family-based residence permits",
        "category": "immigration"
    },
    
    # Belastingdienst (Tax Service)
    {
        "url": "https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/belastingdienst/prive",
        "title": "Belastingdienst - Particulieren",
        "description": "Tax information for individuals, income tax, and personal tax returns",
        "category": "taxes"
    },
    {
        "url": "https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/belastingdienst/ondernemers",
        "title": "Belastingdienst - Ondernemers",
        "description": "Tax information for businesses, VAT, and corporate taxes",
        "category": "taxes"
    },
    
    # UWV (Employee Insurance Agency)
    {
        "url": "https://www.uwv.nl/particulieren",
        "title": "UWV - Particulieren",
        "description": "Unemployment benefits, disability benefits, and work reintegration",
        "category": "employment"
    },
    {
        "url": "https://www.uwv.nl/werkgevers",
        "title": "UWV - Werkgevers",
        "description": "Employer services, wage costs, and employment regulations",
        "category": "employment"
    },
    
    # DUO (Education Executive Agency)
    {
        "url": "https://duo.nl/particulier/",
        "title": "DUO - Studenten",
        "description": "Student finance, loans, grants, and educational expenses",
        "category": "education"
    },
    
    # SVB (Social Insurance Bank)
    {
        "url": "https://www.svb.nl/nl",
        "title": "SVB - Sociale Verzekeringsbank",
        "description": "AOW pension, ANW survivor benefits, and child benefits",
        "category": "pensions"
    },
    
    # Zorginstituut Nederland
    {
        "url": "https://www.zorginstituutnederland.nl/",
        "title": "Zorginstituut Nederland",
        "description": "Healthcare insurance, coverage decisions, and healthcare policy",
        "category": "healthcare"
    },
    
    # RDW (Vehicle Authority)
    {
        "url": "https://www.rdw.nl/particulier",
        "title": "RDW - Voertuigen",
        "description": "Vehicle registration, driving licenses, and vehicle inspections",
        "category": "transportation"
    },
    
    # Overheid.nl - Specific Topics
    {
        "url": "https://www.overheid.nl",
        "title": "Overheid.nl",
        "description": "Central portal for all government information and services",
        "category": "general"
    },
    
    # Gemeente (Municipality) Services
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/gemeenten",
        "title": "Gemeenten",
        "description": "Municipal services, local government, and city services",
        "category": "local_government"
    },
    
    # Legal and Justice
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/rechtspraak",
        "title": "Rechtspraak",
        "description": "Judicial system, courts, and legal procedures",
        "category": "legal"
    },
    
    # Business and Entrepreneurship
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/ondernemen",
        "title": "Ondernemen",
        "description": "Starting a business, permits, regulations, and business support",
        "category": "business"
    },
    
    # WOO (Wet Openbaarheid van Bestuur) - Freedom of Information Act
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/wet-open-overheid-woo/vraag-en-antwoord/hoe-dien-ik-een-woo-verzoek-in",
        "title": "Rijksoverheid – Hoe dien ik een Woo-verzoek in",
        "description": "How to submit a WOO (Freedom of Information) request",
        "category": "woo"
    },
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/wet-open-overheid-woo",
        "title": "Rijksoverheid – Wet open overheid (Woo)",
        "description": "Information about the Dutch Freedom of Information Act (WOO)",
        "category": "woo"
    },
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/wet-open-overheid-woo/vraag-en-antwoord/waar-woo-verzoek-indienen",
        "title": "Rijksoverheid – Waar Woo-verzoek indienen",
        "description": "Where to submit a WOO request",
        "category": "woo"
    },
    {
        "url": "https://www.rijksoverheid.nl/onderwerpen/wet-open-overheid-woo/documenten",
        "title": "Rijksoverheid – Documenten over Woo",
        "description": "Documents related to WOO (Freedom of Information Act)",
        "category": "woo"
    },
    {
        "url": "https://wetten.overheid.nl/BWBR0045754/",
        "title": "Wetten.nl – Regeling Wet open overheid",
        "description": "Official legal text of the WOO regulation",
        "category": "woo"
    },
    {
        "url": "https://www.nwo.nl/een-woo-verzoek-indienen",
        "title": "NWO – Een Woo-verzoek indienen",
        "description": "How to submit a WOO request to NWO (Dutch Research Council)",
        "category": "woo"
    },
    {
        "url": "https://justis.nl/justis/indienen-verzoek-wet-open-overheid-woo-verzoek",
        "title": "Justis – Woo-verzoek indienen",
        "description": "How to submit a WOO request to Justis",
        "category": "woo"
    },
    {
        "url": "https://www.uwv.nl/nl/wet-open-overheid/woo-verzoek-indienen",
        "title": "UWV – Woo-verzoek indienen",
        "description": "How to submit a WOO request to UWV (Employee Insurance Agency)",
        "category": "woo"
    },
    {
        "url": "https://www.zorginstituutnederland.nl/over-ons/bezwaar-klacht-woo-verzoek-of-avg-inzageverzoek/woo-verzoek",
        "title": "Zorginstituut Nederland – Woo-verzoek",
        "description": "How to submit a WOO request to Zorginstituut Nederland",
        "category": "woo"
    },
    {
        "url": "https://www.rekenkamer.nl/contact/ik-heb-een-woo-verzoek",
        "title": "Algemene Rekenkamer – Ik heb een Woo-verzoek",
        "description": "WOO request information for Algemene Rekenkamer (Court of Audit)",
        "category": "woo"
    },
    {
        "url": "https://www.valkenswaard.nl/informatie-opvragen-bij-gemeente-wet-open-overheid-woo",
        "title": "Gemeente Valkenswaard – Informatie opvragen bij gemeente (Woo)",
        "description": "WOO request information for Municipality of Valkenswaard",
        "category": "woo"
    },
    {
        "url": "https://www.arnhem.nl/product/woo-verzoek-indienen/",
        "title": "Gemeente Arnhem – Woo-verzoek indienen",
        "description": "How to submit a WOO request to Municipality of Arnhem",
        "category": "woo"
    },
    {
        "url": "https://gemeente.groningen.nl/woo-verzoek",
        "title": "Gemeente Groningen – Woo-verzoek",
        "description": "WOO request information for Municipality of Groningen",
        "category": "woo"
    },
    {
        "url": "https://www.amstelveen.nl/woo-verzoek-indienen",
        "title": "Gemeente Amstelveen – Woo-verzoek indienen",
        "description": "How to submit a WOO request to Municipality of Amstelveen",
        "category": "woo"
    },
    {
        "url": "https://www.waarderingskamer.nl/wet-open-overheid/woo-documents",
        "title": "Waarderingskamer – Woo-documenten",
        "description": "WOO documents from Waarderingskamer (Property Valuation Board)",
        "category": "woo"
    },
    {
        "url": "https://www.om.nl/onderwerpen/wet-open-overheid/woo-documenten",
        "title": "Openbaar Ministerie – Woo-documenten",
        "description": "WOO documents from Openbaar Ministerie (Public Prosecution Service)",
        "category": "woo"
    },
    {
        "url": "https://www.rvo.nl/onderwerpen/juridische-zaken/woo",
        "title": "RVO – Wet open overheid",
        "description": "WOO information from RVO (Netherlands Enterprise Agency)",
        "category": "woo"
    },
    {
        "url": "https://openresearch.amsterdam/nl/page/98600/de-wet-open-overheid-en-amsterdam",
        "title": "OpenResearch Amsterdam – De Wet open overheid en Amsterdam",
        "description": "WOO information and research in Amsterdam",
        "category": "woo"
    },
    {
        "url": "https://www.belastingdienst.nl/wps/wcm/connect/nl/over-de-belastingdienst/content/woo-verzoek-indienen",
        "title": "Belastingdienst – Woo-verzoek indienen",
        "description": "How to submit a WOO request to Belastingdienst (Tax Service)",
        "category": "woo"
    },
    {
        "url": "https://www.igj.nl/contact/wet-open-overheid",
        "title": "IGJ – Wet open overheid",
        "description": "WOO information from IGJ (Health and Youth Care Inspectorate)",
        "category": "woo"
    },
    {
        "url": "https://www.nza.nl/over-de-nza/openbaarmakingen/woo-verzoeken",
        "title": "NZa – Woo-verzoeken",
        "description": "WOO requests from NZa (Dutch Healthcare Authority)",
        "category": "woo"
    },
    {
        "url": "https://autoriteitpersoonsgegevens.nl/nl/onderwerpen/wet-open-overheid",
        "title": "Autoriteit Persoonsgegevens – Woo-verzoek",
        "description": "WOO information from Autoriteit Persoonsgegevens (Data Protection Authority)",
        "category": "woo"
    },
    {
        "url": "https://www.afm.nl/nl-nl/over-de-afm/woo",
        "title": "AFM – Woo-verzoek indienen",
        "description": "WOO information from AFM (Financial Markets Authority)",
        "category": "woo"
    },
    {
        "url": "https://www.dnb.nl/over-ons/organisatie/woo/",
        "title": "DNB – Wet open overheid",
        "description": "WOO information from DNB (Dutch Central Bank)",
        "category": "woo"
    },
    {
        "url": "https://www.cbs.nl/nl-nl/over-ons/organisatie/openbaarheid/woo",
        "title": "CBS – Wet open overheid",
        "description": "WOO information from CBS (Statistics Netherlands)",
        "category": "woo"
    },
    {
        "url": "https://www.nvwa.nl/over-de-nvwa/woo",
        "title": "NVWA – Woo-verzoeken",
        "description": "WOO requests from NVWA (Netherlands Food and Consumer Product Safety Authority)",
        "category": "woo"
    },
    {
        "url": "https://www.rijkswaterstaat.nl/over-ons/organisatie/wet-open-overheid",
        "title": "Rijkswaterstaat – Woo-verzoek indienen of inzien",
        "description": "WOO requests from Rijkswaterstaat (Public Works and Water Management)",
        "category": "woo"
    },
    {
        "url": "https://www.ilent.nl/onderwerpen/wet-open-overheid",
        "title": "ILT – Woo-verzoeken",
        "description": "WOO requests from ILT (Human Environment and Transport Inspectorate)",
        "category": "woo"
    },
    {
        "url": "https://www.amsterdam.nl/woo",
        "title": "Gemeente Amsterdam – Wet open overheid",
        "description": "WOO information for Municipality of Amsterdam",
        "category": "woo"
    },
    {
        "url": "https://www.rotterdam.nl/woo-verzoek",
        "title": "Gemeente Rotterdam – Woo-verzoek indienen",
        "description": "How to submit a WOO request to Municipality of Rotterdam",
        "category": "woo"
    },
    {
        "url": "https://www.utrecht.nl/woo",
        "title": "Gemeente Utrecht – Woo-publicaties",
        "description": "WOO publications from Municipality of Utrecht",
        "category": "woo"
    },
    {
        "url": "https://www.denhaag.nl/nl/in-de-stad/nieuws/wet-open-overheid-woo.htm",
        "title": "Gemeente Den Haag – Wet open overheid",
        "description": "WOO information for Municipality of The Hague",
        "category": "woo"
    },
    {
        "url": "https://www.eindhoven.nl/woo",
        "title": "Gemeente Eindhoven – Wet open overheid",
        "description": "WOO information for Municipality of Eindhoven",
        "category": "woo"
    },
    {
        "url": "https://www.haarlem.nl/woo",
        "title": "Gemeente Haarlem – Woo-verzoek indienen",
        "description": "How to submit a WOO request to Municipality of Haarlem",
        "category": "woo"
    },
    {
        "url": "https://gemeente.groningen.nl/woo-publicaties",
        "title": "Gemeente Groningen – Woo-publicaties",
        "description": "WOO publications from Municipality of Groningen",
        "category": "woo"
    },
    {
        "url": "https://www.tilburg.nl/woo",
        "title": "Gemeente Tilburg – Woo-verzoeken",
        "description": "WOO requests for Municipality of Tilburg",
        "category": "woo"
    },
    {
        "url": "https://www.leiden.nl/woo",
        "title": "Gemeente Leiden – Wet open overheid",
        "description": "WOO information for Municipality of Leiden",
        "category": "woo"
    },
    {
        "url": "https://www.enschede.nl/woo",
        "title": "Gemeente Enschede – Woo-verzoeken",
        "description": "WOO requests for Municipality of Enschede",
        "category": "woo"
    },
    {
        "url": "https://www.kadaster.nl/woo",
        "title": "Kadaster – Woo-verzoeken",
        "description": "WOO requests from Kadaster (Land Registry)",
        "category": "woo"
    },
    {
        "url": "https://www.emissieautoriteit.nl/wet-open-overheid",
        "title": "Nederlandse Emissieautoriteit – Wet open overheid",
        "description": "WOO information from Nederlandse Emissieautoriteit (Netherlands Emissions Authority)",
        "category": "woo"
    },
    {
        "url": "https://www.inspectieszw.nl/contact/wet-open-overheid",
        "title": "Inspectie SZW – Woo-verzoeken",
        "description": "WOO requests from Inspectie SZW (Labour Inspectorate)",
        "category": "woo"
    },
    {
        "url": "https://duo.nl/particulier/woo-verzoek.jsp",
        "title": "DUO – Woo-verzoek indienen",
        "description": "How to submit a WOO request to DUO (Education Executive Agency)",
        "category": "woo"
    },
    {
        "url": "https://www.cjib.nl/woo",
        "title": "CJIB – Wet open overheid",
        "description": "WOO information from CJIB (Central Fine Collection Agency)",
        "category": "woo"
    },
    {
        "url": "https://www.rvig.nl/onderwerpen/wet-open-overheid",
        "title": "Rijksdienst voor Identiteitsgegevens – Woo-verzoek",
        "description": "WOO requests from RVIG (Identity Data Service)",
        "category": "woo"
    },
    {
        "url": "https://www.nlarbeidsinspectie.nl/onderwerpen/wet-open-overheid",
        "title": "Nederlandse Arbeidsinspectie – Woo-verzoeken",
        "description": "WOO requests from Nederlandse Arbeidsinspectie (Dutch Labour Inspectorate)",
        "category": "woo"
    },
    {
        "url": "https://www.tno.nl/nl/over-tno/organisatie/woo-verzoek/",
        "title": "TNO – Woo-verzoek",
        "description": "WOO requests from TNO (Netherlands Organisation for Applied Scientific Research)",
        "category": "woo"
    },
    {
        "url": "https://www.sodm.nl/onderwerpen/wet-open-overheid",
        "title": "SodM – Woo-verzoeken",
        "description": "WOO requests from SodM (State Supervision of Mines)",
        "category": "woo"
    },
    {
        "url": "https://www.acm.nl/nl/over-acm/openbaarheid/woo",
        "title": "ACM – Woo-verzoeken",
        "description": "WOO requests from ACM (Authority for Consumers and Markets)",
        "category": "woo"
    },
    {
        "url": "https://ind.nl/en/service-contact/contact-with-ind/submit-a-woo-request",
        "title": "IND – Submit a Woo request",
        "description": "How to submit a WOO request to IND (Immigration and Naturalization Service)",
        "category": "woo"
    },
    {
        "url": "https://www.uva.nl/over-de-uva/organisatie/juridische-zaken/wet-open-overheid/wet-open-overheid.html",
        "title": "Universiteit van Amsterdam – Wet open overheid",
        "description": "WOO information from University of Amsterdam",
        "category": "woo"
    },
    {
        "url": "https://www.zoetermeer.nl/informatie-opvragen-of-woo-verzoek-doen",
        "title": "Gemeente Zoetermeer – Woo-verzoek",
        "description": "WOO requests for Municipality of Zoetermeer",
        "category": "woo"
    },
    {
        "url": "https://www.almere.nl/bestuur-en-organisatie/wet-open-overheid-woo/informatie-of-woo-verzoek-indienen",
        "title": "Gemeente Almere – Woo-verzoek",
        "description": "WOO requests for Municipality of Almere",
        "category": "woo"
    },
    {
        "url": "https://www.justid.nl/woo",
        "title": "JustID – Wet open overheid",
        "description": "WOO information from JustID",
        "category": "woo"
    },
    {
        "url": "https://www.noordwijk.nl/onderwerp/overheidsinformatie-en-regelgeving/wet-open-overheid-woo/woo-verzoek-indienen/",
        "title": "Gemeente Noordwijk – Woo-verzoek indienen",
        "description": "How to submit a WOO request to Municipality of Noordwijk",
        "category": "woo"
    },
    {
        "url": "https://www.ccmo.nl/onderzoekers/wet-en-regelgeving-voor-medisch-wetenschappelijk-onderzoek/wetten/wet-open-overheid-woo",
        "title": "CCMO – Wet open overheid",
        "description": "WOO information from CCMO (Central Committee on Research Involving Human Subjects)",
        "category": "woo"
    },
    {
        "url": "https://www.westerkwartier.nl/informatieverzoek-en-woo-verzoek",
        "title": "Gemeente Westerkwartier – Woo-verzoek",
        "description": "WOO requests for Municipality of Westerkwartier",
        "category": "woo"
    },
    {
        "url": "https://www.coa.nl/nl/wet-open-overheid-woo",
        "title": "COA – Wet open overheid",
        "description": "WOO information from COA (Central Agency for the Reception of Asylum Seekers)",
        "category": "woo"
    },
    {
        "url": "https://www.open-overheid.nl/",
        "title": "Programma Open Overheid – Home",
        "description": "Open Government Program homepage with WOO information",
        "category": "woo"
    },
    {
        "url": "https://www.nieuwegein.nl/gemeente-bestuur-en-organisatie/wet-en-regelgeving/woo-verzoek",
        "title": "Gemeente Nieuwegein – Woo-verzoek",
        "description": "WOO requests for Municipality of Nieuwegein",
        "category": "woo"
    },
    {
        "url": "https://www.zwolle.nl/woo",
        "title": "Gemeente Zwolle – Woo-verzoeken",
        "description": "WOO requests for Municipality of Zwolle",
        "category": "woo"
    },
    {
        "url": "https://www.breda.nl/woo",
        "title": "Gemeente Breda – Wet open overheid",
        "description": "WOO information for Municipality of Breda",
        "category": "woo"
    },
    {
        "url": "https://www.apeldoorn.nl/woo",
        "title": "Gemeente Apeldoorn – Woo-verzoeken",
        "description": "WOO requests for Municipality of Apeldoorn",
        "category": "woo"
    },
    {
        "url": "https://www.nijmegen.nl/woo",
        "title": "Gemeente Nijmegen – Woo-verzoeken",
        "description": "WOO requests for Municipality of Nijmegen",
        "category": "woo"
    },
    {
        "url": "https://www.alkmaar.nl/woo",
        "title": "Gemeente Alkmaar – Woo-verzoeken",
        "description": "WOO requests for Municipality of Alkmaar",
        "category": "woo"
    },
    {
        "url": "https://www.dordrecht.nl/woo",
        "title": "Gemeente Dordrecht – Woo-verzoek",
        "description": "WOO requests for Municipality of Dordrecht",
        "category": "woo"
    },
    {
        "url": "https://www.leeuwarden.nl/woo",
        "title": "Gemeente Leeuwarden – Woo-verzoeken",
        "description": "WOO requests for Municipality of Leeuwarden",
        "category": "woo"
    },
    {
        "url": "https://www.gemeentemaastricht.nl/woo",
        "title": "Gemeente Maastricht – Woo-verzoeken",
        "description": "WOO requests for Municipality of Maastricht",
        "category": "woo"
    },
    {
        "url": "https://www.haarlemmermeer.nl/woo",
        "title": "Gemeente Haarlemmermeer – Woo-verzoeken",
        "description": "WOO requests for Municipality of Haarlemmermeer",
        "category": "woo"
    },
    {
        "url": "https://www.deventer.nl/woo",
        "title": "Gemeente Deventer – Woo-verzoeken",
        "description": "WOO requests for Municipality of Deventer",
        "category": "woo"
    },
    {
        "url": "https://www.amersfoort.nl/woo",
        "title": "Gemeente Amersfoort – Woo-verzoeken",
        "description": "WOO requests for Municipality of Amersfoort",
        "category": "woo"
    },
    {
        "url": "https://www.emmen.nl/woo",
        "title": "Gemeente Emmen – Woo-verzoeken",
        "description": "WOO requests for Municipality of Emmen",
        "category": "woo"
    },
    {
        "url": "https://www.helmond.nl/woo",
        "title": "Gemeente Helmond – Woo-verzoeken",
        "description": "WOO requests for Municipality of Helmond",
        "category": "woo"
    },
    {
        "url": "https://www.venlo.nl/woo",
        "title": "Gemeente Venlo – Woo-verzoeken",
        "description": "WOO requests for Municipality of Venlo",
        "category": "woo"
    },
    {
        "url": "https://www.zaanstad.nl/woo",
        "title": "Gemeente Zaanstad – Woo-verzoeken",
        "description": "WOO requests for Municipality of Zaanstad",
        "category": "woo"
    },
    {
        "url": "https://www.almelo.nl/woo",
        "title": "Gemeente Almelo – Woo-verzoeken",
        "description": "WOO requests for Municipality of Almelo",
        "category": "woo"
    },
    {
        "url": "https://www.sittard-geleen.nl/woo",
        "title": "Gemeente Sittard-Geleen – Woo-verzoeken",
        "description": "WOO requests for Municipality of Sittard-Geleen",
        "category": "woo"
    },
    {
        "url": "https://www.lelystad.nl/woo",
        "title": "Gemeente Lelystad – Woo-verzoeken",
        "description": "WOO requests for Municipality of Lelystad",
        "category": "woo"
    },
    {
        "url": "https://www.gouda.nl/woo",
        "title": "Gemeente Gouda – Woo-verzoeken",
        "description": "WOO requests for Municipality of Gouda",
        "category": "woo"
    },
    {
        "url": "https://www.assen.nl/woo",
        "title": "Gemeente Assen – Woo-verzoeken",
        "description": "WOO requests for Municipality of Assen",
        "category": "woo"
    },
    {
        "url": "https://www.bergenopzoom.nl/woo",
        "title": "Gemeente Bergen op Zoom – Woo-verzoeken",
        "description": "WOO requests for Municipality of Bergen op Zoom",
        "category": "woo"
    },
    {
        "url": "https://www.capelleaandenijssel.nl/woo",
        "title": "Gemeente Capelle aan den IJssel – Woo-verzoeken",
        "description": "WOO requests for Municipality of Capelle aan den IJssel",
        "category": "woo"
    },
    {
        "url": "https://www.schiedam.nl/woo",
        "title": "Gemeente Schiedam – Woo-verzoeken",
        "description": "WOO requests for Municipality of Schiedam",
        "category": "woo"
    },
    {
        "url": "https://www.ede.nl/woo",
        "title": "Gemeente Ede – Woo-verzoeken",
        "description": "WOO requests for Municipality of Ede",
        "category": "woo"
    },
    {
        "url": "https://www.hilversum.nl/woo",
        "title": "Gemeente Hilversum – Woo-verzoeken",
        "description": "WOO requests for Municipality of Hilversum",
        "category": "woo"
    },
    {
        "url": "https://www.harderwijk.nl/woo",
        "title": "Gemeente Harderwijk – Woo-verzoeken",
        "description": "WOO requests for Municipality of Harderwijk",
        "category": "woo"
    },
    {
        "url": "https://www.katwijk.nl/woo",
        "title": "Gemeente Katwijk – Woo-verzoeken",
        "description": "WOO requests for Municipality of Katwijk",
        "category": "woo"
    },
    {
        "url": "https://www.hoorn.nl/woo",
        "title": "Gemeente Hoorn – Woo-verzoeken",
        "description": "WOO requests for Municipality of Hoorn",
        "category": "woo"
    },
    {
        "url": "https://www.roosendaal.nl/woo",
        "title": "Gemeente Roosendaal – Woo-verzoeken",
        "description": "WOO requests for Municipality of Roosendaal",
        "category": "woo"
    },
    {
        "url": "https://www.vlaardingen.nl/woo",
        "title": "Gemeente Vlaardingen – Woo-verzoeken",
        "description": "WOO requests for Municipality of Vlaardingen",
        "category": "woo"
    },
    {
        "url": "https://www.middelburg.nl/woo",
        "title": "Gemeente Middelburg – Woo-verzoeken",
        "description": "WOO requests for Municipality of Middelburg",
        "category": "woo"
    },
    {
        "url": "https://www.heerlen.nl/woo",
        "title": "Gemeente Heerlen – Woo-verzoeken",
        "description": "WOO requests for Municipality of Heerlen",
        "category": "woo"
    },
]


def get_sources_by_category(category: str = None):
    """
    Get government sources, optionally filtered by category.
    
    Args:
        category: Optional category to filter by
        
    Returns:
        List of source dictionaries
    """
    if category:
        return [s for s in GOVERNMENT_SOURCES if s.get("category") == category]
    return GOVERNMENT_SOURCES


def get_sources_info():
    """
    Get a formatted list of all sources with their descriptions.
    Useful for LLM prompt context.
    
    Returns:
        String with formatted source information
    """
    info_lines = []
    for i, source in enumerate(GOVERNMENT_SOURCES, 1):
        info_lines.append(
            f"{i}. URL: {source['url']}\n"
            f"   Title: {source['title']}\n"
            f"   Description: {source['description']}\n"
            f"   Category: {source['category']}\n"
        )
    return "\n".join(info_lines)


def get_urls_for_categories(categories: list):
    """
    Get URLs for specific categories.
    
    Args:
        categories: List of category strings
        
    Returns:
        List of URLs
    """
    urls = []
    for source in GOVERNMENT_SOURCES:
        if source.get("category") in categories:
            urls.append(source["url"])
    return urls

