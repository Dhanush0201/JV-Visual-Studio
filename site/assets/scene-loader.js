// One attempt per scene. Failure is a settled result, retried only by user action.
export function createSceneLoader({ create, prepare, dispose, onError = () => {} }) {
  const scenes = Object.create(null);
  function loadScene(key, { retry = false } = {}) {
    const current = scenes[key];
    if (current && !(retry && current.failed)) return current.promise;
    if (current) dispose(current);
    const scene = create(key);
    scenes[key] = scene;
    scene.promise = Promise.resolve()
      .then(() => prepare(scene))
      .then(() => { scene.ready = true; return scene; }, error => {
        scene.failed = true;
        scene.error = error;
        onError(scene, error);
        return scene;
      });
    return scene.promise;
  }
  return { scenes, loadScene };
}
