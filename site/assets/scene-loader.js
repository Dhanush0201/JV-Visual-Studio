// One attempt per scene. Failure is a settled result, retried only by user action.
export function createSceneLoader({ create, prepare, dispose, onReady = () => {}, onError = () => {} }) {
  const scenes = Object.create(null);
  function loadScene(key, { retry = false } = {}) {
    const current = scenes[key];
    if (current && !(retry && current.failed)) return current.promise;
    if (current) dispose(current);
    const scene = create(key);
    scenes[key] = scene;
    scene.promise = Promise.resolve()
      .then(() => prepare(scene))
      .then(() => { scene.ready = true; onReady(scene); return scene; }, error => {
        scene.failed = true;
        scene.error = error;
        onError(scene, error);
        return scene;
      });
    return scene.promise;
  }
  return { scenes, loadScene };
}

// Start independent downloads together. Handle optional failures immediately so a
// rejected landscape request cannot become unhandled while the building loads.
export function startSceneAssets({ environment, sky, model, plants }) {
  const start = task => Promise.resolve().then(task);
  return {
    base: Promise.all([start(environment), start(sky), start(model)]),
    plants: plants ? start(plants).then(value => ({ value }), error => ({ error })) : Promise.resolve(null)
  };
}
