'use client';

interface CrawledWebsite {
  url: string;
  title?: string;
  domain?: string;
}

interface CrawledWebsitesListProps {
  websites: CrawledWebsite[];
}

function getFaviconUrl(url: string): string {
  try {
    const urlObj = new URL(url);
    // Use multiple fallback methods for favicons
    // Method 1: Try direct favicon.ico
    // Method 2: Use Google's favicon service
    return `https://www.google.com/s2/favicons?domain=${urlObj.hostname}&sz=64`;
  } catch {
    return '';
  }
}

function getDomainName(url: string): string {
  try {
    const urlObj = new URL(url);
    return urlObj.hostname.replace('www.', '');
  } catch {
    return url;
  }
}

export function CrawledWebsitesList({ websites }: CrawledWebsitesListProps) {
  if (!websites || websites.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 space-y-2">
      <p className="text-xs font-medium text-gray-600 mb-2">Crawled Websites:</p>
      {websites.map((website, index) => {
        const faviconUrl = getFaviconUrl(website.url);
        const domainName = website.domain || getDomainName(website.url);
        const displayTitle = website.title || domainName;

        return (
          <a
            key={index}
            href={website.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors border border-gray-200 group"
          >
            <div className="w-6 h-6 flex-shrink-0 flex items-center justify-center">
              {faviconUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={faviconUrl}
                  alt={`${domainName} favicon`}
                  className="w-6 h-6 object-contain"
                  onError={(e) => {
                    // Show placeholder if favicon fails
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                    const placeholder = target.nextElementSibling as HTMLElement;
                    if (placeholder) placeholder.style.display = 'flex';
                  }}
                />
              ) : null}
              <div
                className="w-6 h-6 rounded bg-gray-200 flex items-center justify-center text-xs font-medium text-gray-600"
                style={{ display: faviconUrl ? 'none' : 'flex' }}
              >
                {domainName.charAt(0).toUpperCase()}
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate group-hover:text-gray-700">
                {displayTitle}
              </p>
              <p className="text-xs text-gray-500 truncate">
                {domainName}
              </p>
            </div>
          </a>
        );
      })}
    </div>
  );
}

