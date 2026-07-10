export class APIService {
    constructor() {
        this.baseUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? 'http://127.0.0.1:8000'
            : 'https://your-backend.onrender.com'; // No trailing slash
    }

    async fetchScenario(id, mode = 'both') {
        try {
            // Append the solver mode as a query parameter
            const response = await fetch(`${this.baseUrl}/scenario/${id}?solver=${mode}`, { cache: 'no-store' });
            return await response.json();
        } catch (err) {
            console.error(`Failed to reach backend at ${this.baseUrl}. Is guy/server.py running?`, err);
            return { error: 'Network failure' };
        }
    }

    async fetchKKTQuery(pointVec, timeInt) {
        try {
            const response = await fetch(`${this.baseUrl}/kkt_query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                cache: 'no-store', // Universally disable caching for all API interactions
                body: JSON.stringify({ point: [pointVec.x, pointVec.y, pointVec.z], t: timeInt }),
            });
            return await response.json();
        } catch (err) {
            console.error('KKT query failed:', err);
            return null;
        }
    }
}