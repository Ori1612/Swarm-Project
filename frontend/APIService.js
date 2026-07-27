export class APIService {
    constructor() {
        this.baseUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? 'http://127.0.0.1:8000'
            : 'https://your-backend.onrender.com'; // No trailing slash
    }

    async fetchScenario(id, mode = 'both') {
        try {
            // Load pre-calculated scenario JSON directly from static cache folder
            const response = await fetch(`/cache_data/${id}.json`, { cache: 'no-store' });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (err) {
            console.error(`Failed to load scenario ${id} from static cache:`, err);
            return { error: 'Network failure' };
        }
    }

    async fetchKKTQuery(pointVec, timeInt) {
        // Static fallback since Netlify cannot execute server-side Python endpoints
        return { hyperplanes: [] };
    }
}