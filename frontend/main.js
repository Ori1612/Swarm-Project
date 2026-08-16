// Section 5.1 -- Application orchestrator: fetch payloads + instantiate classes.
import { SceneManager } from './SceneManager.js';
import { EnvironmentBuilder } from './EnvironmentBuilder.js';
import { UIManager } from './UIManager.js';
import { APIService } from './APIService.js';

const apiService = new APIService();
const sceneManager = new SceneManager();
const envBuilder = new EnvironmentBuilder(sceneManager.scene);
const uiManager = new UIManager(sceneManager, envBuilder, apiService);

// Load the restored scenario from local storage (or fallback to the dropdown selection)
const initialScenario = document.getElementById('scenario-select').value || 'cyber_city';
uiManager.loadScenario(initialScenario);

function animate() {
    requestAnimationFrame(animate);
    
    // Check if we are tracking a drone (3rd or 1st person)
    if (uiManager.cameraMode !== 'free') {
        const targetDrone = sceneManager.getDrone(uiManager.targetDroneIdx);
        sceneManager.updateCameraTracking(targetDrone, uiManager.cameraMode);
    }
    
    uiManager.update();
    sceneManager.render();
}
animate();
console.log("System Status: Live");