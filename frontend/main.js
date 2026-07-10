// Section 5.1 -- Application orchestrator: fetch payloads + instantiate classes.
import { SceneManager } from './SceneManager.js';
import { EnvironmentBuilder } from './EnvironmentBuilder.js';
import { UIManager } from './UIManager.js';
import { APIService } from './APIService.js';

const apiService = new APIService();
const sceneManager = new SceneManager();
const envBuilder = new EnvironmentBuilder(sceneManager.scene);
const uiManager = new UIManager(sceneManager, envBuilder, apiService);

// Load the default scenario (matches the first <option> in index.html).
uiManager.loadScenario('cyber_city');

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
