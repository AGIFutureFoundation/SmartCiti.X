// AUTHORED shim (not upstream awaitqueue): the one API the Reactor SDK uses - push(task, name) runs
// tasks strictly one after another and resolves/rejects with each task's own result.
export class AwaitQueue {
  constructor() { this._tail = Promise.resolve(); this._closed = false; }
  push(task, name) {
    if (this._closed) return Promise.reject(new Error('AwaitQueue closed' + (name ? ' (' + name + ')' : '')));
    const run = this._tail.then(() => task());
    this._tail = run.then(() => undefined, () => undefined);
    return run;
  }
  stop() { this._closed = true; }
  close() { this._closed = true; }
}
export default AwaitQueue;
