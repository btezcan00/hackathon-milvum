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

