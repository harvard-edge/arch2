/*
 * XR Feature Point Detection 2D Filtering Kernel
 * ===============================================
 * Representative inner-loop spatial filtering kernel used in mobile XR tracking,
 * visual odometry, and corner score computation over 256x256 image frames.
 */

#include <stdint.h>

#define FRAME_WIDTH  256
#define FRAME_HEIGHT 256
#define KERNEL_DIM   5

// Baseline Scalar C Implementation
void xr_filter_baseline(
    const uint8_t * __restrict__ src,
    int16_t * __restrict__ dst,
    const int8_t * __restrict__ weights
) {
    for (int y = 2; y < FRAME_HEIGHT - 2; y++) {
        for (int x = 2; x < FRAME_WIDTH - 2; x++) {
            int32_t acc = 0;
            #pragma unroll 5
            for (int ky = -2; ky <= 2; ky++) {
                for (int kx = -2; kx <= 2; kx++) {
                    int p_idx = (y + ky) * FRAME_WIDTH + (x + kx);
                    int w_idx = (ky + 2) * KERNEL_DIM + (kx + 2);
                    acc += (int32_t)src[p_idx] * (int32_t)weights[w_idx];
                }
            }
            dst[y * FRAME_WIDTH + x] = (int16_t)(acc >> 4);
        }
    }
}
