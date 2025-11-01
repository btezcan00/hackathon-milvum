'use client';

import { Globe, Loader2 } from 'lucide-react';

export interface CrawlingWebsite {
  domain: string;
  title: string;
  entry_url: string;
}

interface CrawlingWebsitesProps {
  websites: CrawlingWebsite[];
  isCrawling?: boolean;
}

export function CrawlingWebsites({ websites, isCrawling = true }: CrawlingWebsitesProps) {
  if (websites.length === 0) {
    return null;
  }

  // Generate favicon URL - use Google's favicon service as fallback
  const getFaviconUrl = (domain: string) => {
    // Try to get favicon from domain
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  };

  return (
    <div className="flex flex-col gap-2 p-3 bg-gray-50 border border-gray-200 rounded">
      <div className="flex items-center gap-2 mb-1">
        <Globe className="h-4 w-4 text-[#154274]" />
        <span className="text-xs font-bold text-gray-700" style={{ fontFamily: 'Verdana, sans-serif' }}>
          {isCrawling ? 'Websites worden gecrawld...' : 'Gecrawlde websites:'}
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {websites.map((website, index) => (
          <div
            key={index}
            className="flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded shadow-sm hover:shadow-md transition-shadow"
          >
            {isCrawling && (
              <Loader2 className="h-3 w-3 animate-spin text-[#154274]" />
            )}
            <img
              src={getFaviconUrl(website.domain)}
              alt={website.domain}
              className="w-4 h-4 rounded-sm"
              onError={(e) => {
                // Fallback to globe icon if favicon fails to load
                const target = e.target as HTMLImageElement;
                target.style.display = 'none';
                const parent = target.parentElement;
                if (parent && !parent.querySelector('.fallback-icon')) {
                  const icon = document.createElement('div');
                  icon.className = 'fallback-icon w-4 h-4 flex items-center justify-center';
                  icon.innerHTML = '<svg class="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" /></svg>';
                  parent.insertBefore(icon, target);
                }
              }}
            />
            <div className="flex flex-col min-w-0">
              <span 
                className="text-xs font-semibold text-gray-800 truncate max-w-[200px]" 
                style={{ fontFamily: 'Verdana, sans-serif' }}
                title={website.title}
              >
                {website.title || website.domain}
              </span>
              <span 
                className="text-[10px] text-gray-500 truncate max-w-[200px]" 
                style={{ fontFamily: 'Verdana, sans-serif' }}
                title={website.domain}
              >
                {website.domain}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

