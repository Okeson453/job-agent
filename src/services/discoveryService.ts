import { Job } from '../types';

export interface DiscoverySourceConfig {
  id: string;
  name: string;
  type: 'greenhouse' | 'lever' | 'remoteok' | 'himalayas' | 'indeed' | 'wellfound';
  enabled: boolean;
  pollIntervalMinutes: number;
  rateLimitPerMinute: number;
}

export const DEFAULT_SOURCES: DiscoverySourceConfig[] = [
  { id: 'greenhouse', name: 'Greenhouse Public Boards', type: 'greenhouse', enabled: true, pollIntervalMinutes: 30, rateLimitPerMinute: 20 },
  { id: 'lever', name: 'Lever Direct Feeds', type: 'lever', enabled: true, pollIntervalMinutes: 45, rateLimitPerMinute: 15 },
  { id: 'remoteok', name: 'RemoteOK API', type: 'remoteok', enabled: true, pollIntervalMinutes: 60, rateLimitPerMinute: 10 },
  { id: 'himalayas', name: 'Himalayas Remote Feed', type: 'himalayas', enabled: true, pollIntervalMinutes: 60, rateLimitPerMinute: 10 },
  { id: 'wellfound', name: 'Wellfound Startup Jobs', type: 'wellfound', enabled: false, pollIntervalMinutes: 120, rateLimitPerMinute: 5 },
  { id: 'indeed', name: 'Indeed Scraper Pipeline', type: 'indeed', enabled: false, pollIntervalMinutes: 180, rateLimitPerMinute: 5 },
];

export async function fetchGreenhouseBoard(boardToken: string): Promise<Job[]> {
  try {
    const url = `https://boards-api.greenhouse.io/v1/boards/${encodeURIComponent(boardToken.trim())}/jobs?content=true`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Greenhouse API responded with HTTP ${response.status}`);
    }
    const data = await response.json();
    const rawJobs = data.jobs || [];

    const companyName = boardToken.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

    return rawJobs.slice(0, 25).map((raw: any) => {
      const title = raw.title || 'Software Engineer';
      const description = raw.content ? raw.content.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim() : '';
      const location = raw.location?.name || 'Remote';
      const isRemote =
        location.toLowerCase().includes('remote') ||
        title.toLowerCase().includes('remote') ||
        description.toLowerCase().includes('remote');

      const techKeywords = ['typescript', 'python', 'react', 'node', 'postgresql', 'redis', 'docker', 'fastapi', 'aws', 'kubernetes', 'graphql'];
      const foundTech = techKeywords.filter((k) =>
        (title + ' ' + description).toLowerCase().includes(k)
      );

      return {
        id: `gh-${boardToken}-${raw.id}`,
        source: 'greenhouse',
        external_id: String(raw.id),
        title,
        company: companyName,
        description: description.slice(0, 1500),
        location,
        remote: isRemote,
        countries: isRemote ? ['Worldwide', 'Nigeria'] : ['United States'],
        employment_type: 'Full-time',
        salary_min: 75000,
        salary_max: 135000,
        salary_currency: 'USD',
        technologies: foundTech.map((t) => t.toUpperCase()),
        seniority: title.toLowerCase().includes('senior') ? 'Senior' : 'Mid',
        application_url: raw.absolute_url || `https://boards.greenhouse.io/${boardToken}/jobs/${raw.id}`,
        state: 'DISCOVERED',
        discovered_at: new Date().toISOString(),
      };
    });
  } catch (err: any) {
    console.warn(`Failed to fetch Greenhouse board '${boardToken}':`, err.message);
    throw err;
  }
}

export function generateSimulatedJobs(source: string, count: number = 3): Job[] {
  const titles = [
    'Senior Distributed Systems Engineer',
    'Full-Stack Developer (React & TypeScript)',
    'Application Security & DevSecOps Engineer',
    'Autonomous Agent Infrastructure Lead',
    'Backend Engineer - High Throughput WebSockets',
  ];
  const companies = [
    'Chronos Security',
    'PulseStream AI',
    'OpenLedger Inc',
    'HyperScale Systems',
    'Aether Quant',
  ];

  const jobs: Job[] = [];
  for (let i = 0; i < count; i++) {
    const title = titles[Math.floor(Math.random() * titles.length)];
    const company = companies[Math.floor(Math.random() * companies.length)];
    const idNum = Math.floor(1000 + Math.random() * 9000);

    jobs.push({
      id: `${source}-${idNum}`,
      source,
      external_id: `ext-${idNum}`,
      title,
      company,
      description: `We are seeking an experienced engineer for ${title} at ${company}. Experience with TypeScript, Python, PostgreSQL, Redis, and high-reliability systems required. Remote-friendly worldwide.`,
      location: 'Remote (Global)',
      remote: true,
      countries: ['Worldwide', 'Nigeria'],
      employment_type: 'Full-time',
      salary_min: 70000 + (idNum % 5) * 5000,
      salary_max: 110000 + (idNum % 5) * 8000,
      salary_currency: 'USD',
      technologies: ['TypeScript', 'Python', 'PostgreSQL', 'Redis', 'Docker'],
      seniority: 'Senior',
      application_url: `https://${source}.com/jobs/${idNum}`,
      state: 'DISCOVERED',
      discovered_at: new Date().toISOString(),
    });
  }
  return jobs;
}
