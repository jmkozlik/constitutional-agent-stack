# Defects — node gitio

none

One observation recorded (not filed — conforming behavior, outside every
done_when bullet and the seeded error contract): git's repo discovery walks
upward, so calling any gitio function with a `repo` path that is a plain
directory *inside* some enclosing repo silently answers from that enclosing
repo (observed: `resolve_commit(".harness/scratch", "HEAD")` from this
worktree returned the worktree's own HEAD, 225e2da3). The git command exits
zero, so per the seeded contract ("raised when the underlying git command
exits non-zero") no GitError is due. Detail in handoff.md.
