// AUTHORED shim: HLS clip playback (hls.js) and MP4 remuxing (mp4box) are not vendored in this bundle.
const refuse = () => { throw new Error('clip playback / recording download is not bundled here'); };
export default new Proxy({}, { get: () => refuse });
export const createFile = refuse;
