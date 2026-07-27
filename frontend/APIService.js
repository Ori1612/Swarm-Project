export class APIService {
    constructor() {
        this.baseUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? 'http://127.0.0.1:8000'
            : 'https://your-backend.onrender.com'; // No trailing slash
    }

    async fetchScenario(id, mode = 'both') {
        try {
            // Map scenario IDs to their correct time horizons (T)
            let T = 30;
            if (id === 'cyber_city') T = 75;
            else if (id === 'torture_track') T = 20;

            let modeStr = mode.toUpperCase();
            
            // Torture track only has a combined BOTH cache file available
            if (id === 'torture_track') {
                modeStr = 'BOTH';
            }

            const filename = `payload_${id}_${modeStr}_${T}.json`;

            // Load pre-calculated scenario JSON from static cache folder
            const response = await fetch(`./cache_data/${filename}`, { cache: 'no-store' });
            if (!response.ok) {
                // Fallback to absolute path root fetch if relative fails
                const fallbackResponse = await fetch(`/cache_data/${filename}`, { cache: 'no-store' });
                if (!fallbackResponse.ok) throw new Error(`HTTP error! status: ${fallbackResponse.status}`);
                return await fallbackResponse.json();
            }
            return await response.json();
        } catch (err) {
            console.error(`Failed to load scenario ${id} (${mode}) from static cache:`, err);
            return { error: 'Network failure' };
        }
    }

    async fetchKKTQuery(pointVec, timeInt) {
        // Static fallback since Netlify cannot execute server-side Python endpoints
        return { hyperplanes: [] };
    }
}