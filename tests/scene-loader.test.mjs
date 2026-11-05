import test from 'node:test';
import assert from 'node:assert/strict';
import { createSceneLoader, startSceneAssets } from '../site/assets/scene-loader.js';

function harness(prepare) {
  const disposed = [], errors = [];
  return {
    ...createSceneLoader({
      create: key => ({ key, ready: false, failed: false }),
      prepare,
      dispose: scene => disposed.push(scene),
      onError: (scene, error) => errors.push({ scene, error })
    }),
    disposed, errors
  };
}

test('concurrent requests share one pending attempt, including retry clicks', async () => {
  let finish, calls = 0;
  const h = harness(() => { calls++; return new Promise(resolve => { finish = resolve; }); });
  const first = h.loadScene('home');
  assert.equal(h.loadScene('home'), first);
  assert.equal(h.loadScene('home', { retry: true }), first);
  await Promise.resolve();
  assert.equal(calls, 1);
  assert.equal(h.scenes.home.ready, false);
  finish();
  const result = await first;
  assert.equal(result.ready, true);
  assert.equal(h.loadScene('home'), first);
});

for (const stage of ['model', 'environment', 'sky', 'scene setup']) {
  test(`${stage} failure settles and an explicit retry recovers`, async () => {
    let calls = 0;
    const error = new Error(`${stage} unavailable`);
    const h = harness(() => { if (++calls === 1) throw error; });
    const failed = await h.loadScene('villa');
    assert.equal(failed.failed, true);
    assert.equal(failed.ready, false);
    assert.equal(failed.error, error);
    assert.equal(await h.loadScene('villa'), failed);
    assert.equal(calls, 1);
    const recovered = await h.loadScene('villa', { retry: true });
    assert.notEqual(recovered, failed);
    assert.equal(recovered.ready, true);
    assert.equal(recovered.failed, false);
    assert.deepEqual(h.disposed, [failed]);
    assert.equal(h.errors.length, 1);
  });
}

test('one failed scene does not block another chapter', async () => {
  const h = harness(scene => { if (scene.key === 'resort') return Promise.reject(new Error('offline')); });
  const [resort, home] = await Promise.all([h.loadScene('resort'), h.loadScene('home')]);
  assert.equal(resort.failed, true);
  assert.equal(home.ready, true);
});

test('independent scene downloads start together, before any one finishes', async () => {
  const started = [], finish = {};
  const download = key => () => {
    started.push(key);
    return new Promise(resolve => { finish[key] = resolve; });
  };
  const assets = startSceneAssets({
    environment: download('environment'), sky: download('sky'),
    model: download('model'), plants: download('plants')
  });
  await Promise.resolve();
  assert.deepEqual(started, ['environment', 'sky', 'model', 'plants']);
  finish.environment('hdr'); finish.sky('sky'); finish.model('glb');
  // A slow optional download must not serialize the three required downloads.
  assert.deepEqual(await assets.base, ['hdr', 'sky', 'glb']);
  finish.plants('landscape');
  assert.deepEqual(await assets.plants, { value: 'landscape' });
});

test('an early optional plant rejection does not reject required assets', async () => {
  const error = new Error('plant model unavailable');
  const assets = startSceneAssets({
    environment: () => 'hdr', sky: () => 'sky', model: () => 'glb',
    plants: () => Promise.reject(error)
  });
  assert.deepEqual(await assets.base, ['hdr', 'sky', 'glb']);
  assert.deepEqual(await assets.plants, { error });
});

test('a required asset failure remains retryable through the scene cache', async () => {
  let missing = true;
  const h = harness(async () => {
    await startSceneAssets({
      environment: () => 'hdr', sky: () => 'sky',
      model: () => { if (missing) throw new Error('missing model'); return 'glb'; }
    }).base;
  });
  assert.equal((await h.loadScene('home')).failed, true);
  missing = false;
  assert.equal((await h.loadScene('home', { retry: true })).ready, true);
});
