// The renderer imports node:crypto only for manifest content hashes, which the
// browser view never uses. This stub keeps the bundle free of Node built-ins.
export const createHash = () => {
  throw new Error("createHash is not available in the nopaste PR Lens bundle");
};
