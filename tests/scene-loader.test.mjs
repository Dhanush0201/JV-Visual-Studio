import test from 'node:test';
import assert from 'node:assert/strict';
import { createSceneLoader } from '../site/assets/scene-loader.js';

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
