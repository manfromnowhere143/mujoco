// A direct C API recorder for source builds; no Python/native ABI substitution.
#include <mujoco/mujoco.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>

int main(int argc, char** argv) {
  if (argc != 3) return 2;
  char error[2048] = {};
  mjModel* m = mj_loadXML(argv[1], nullptr, error, sizeof(error));
  if (!m) { std::fprintf(stderr, "%s\n", error); return 3; }
  mjData* d = mj_makeData(m);
  if (!d) { mj_deleteModel(m); return 4; }
  double seconds = std::atof(argv[2]);
  std::printf("# version=%s dt=%.17g ccd_tolerance=%.17g ccd_iterations=%d\n",
              mj_versionString(), m->opt.timestep, m->opt.ccd_tolerance, m->opt.ccd_iterations);
  if (seconds == 0) {
    mj_forward(m, d);
    std::printf("geom_distance,ncon\n%.17g,%d\n", mj_geomDistance(m, d, 0, 1, 0.05, nullptr), d->ncon);
    std::printf("contact,dist,px,py,pz,nx,ny,nz\n");
    for (int c = 0; c < d->ncon; ++c) {
      const mjContact* k = d->contact + c;
      std::printf("%d,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g\n",
                  c, k->dist, k->pos[0], k->pos[1], k->pos[2], k->frame[0], k->frame[1], k->frame[2]);
    }
  } else {
    if (seconds < 0 || seconds > 60 || m->nq != 7 || m->nv != 6) return 5;
    int steps = std::lround(seconds / m->opt.timestep);
    std::printf("time,x,y,z,qw,qx,qy,qz,vx,vy,vz,wx,wy,wz,ncon,c0dist,c0px,c0py,c0pz,c0nx,c0ny,c0nz\n");
    for (int i = 0; i < steps; ++i) {
      mj_step(m, d);
      std::printf("%.17g", d->time);
      for (int j = 0; j < m->nq; ++j) {
        if (!std::isfinite(d->qpos[j])) return 6;
        std::printf(",%.17g", d->qpos[j]);
      }
      for (int j = 0; j < m->nv; ++j) {
        if (!std::isfinite(d->qvel[j])) return 7;
        std::printf(",%.17g", d->qvel[j]);
      }
      std::printf(",%d", d->ncon);
      if (d->ncon) {
        const mjContact* k = d->contact;
        std::printf(",%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g",
                    k->dist, k->pos[0], k->pos[1], k->pos[2], k->frame[0], k->frame[1], k->frame[2]);
      } else {
        std::printf(",nan,nan,nan,nan,nan,nan,nan");
      }
      std::printf("\n");
    }
  }
  for (int i = 0; i < mjNWARNING; ++i)
    if (d->warning[i].number) std::fprintf(stderr, "warning %d count %d\n", i, d->warning[i].number);
  mj_deleteData(d);
  mj_deleteModel(m);
  return 0;
}
