# Anime4K upstream resources

- Repository: https://github.com/bloc97/Anime4K
- Release: `v4.0.1`; commit: `4029bf701ecaa15f163cdc49cffe5501c1acf410`
- [Original S shader](https://github.com/bloc97/Anime4K/blob/4029bf701ecaa15f163cdc49cffe5501c1acf410/glsl/Upscale/Anime4K_Upscale_CNN_x2_S.glsl) (unmodified)
- [Original M shader](https://github.com/bloc97/Anime4K/blob/4029bf701ecaa15f163cdc49cffe5501c1acf410/glsl/Upscale/Anime4K_Upscale_CNN_x2_M.glsl) (unmodified)
- [Original L shader](https://github.com/bloc97/Anime4K/blob/4029bf701ecaa15f163cdc49cffe5501c1acf410/glsl/Upscale/Anime4K_Upscale_CNN_x2_L.glsl) (unmodified)
- [Original VL shader](https://github.com/bloc97/Anime4K/blob/4029bf701ecaa15f163cdc49cffe5501c1acf410/glsl/Upscale/Anime4K_Upscale_CNN_x2_VL.glsl) (unmodified)
- [Original UL shader](https://github.com/bloc97/Anime4K/blob/4029bf701ecaa15f163cdc49cffe5501c1acf410/glsl/Upscale/Anime4K_Upscale_CNN_x2_UL.glsl) (unmodified)
- [MIT license](LICENSE) (unmodified)

`upscale.py` supplies the mpv hook bindings and runs all shader passes per CNN
invocation: 5 (S), 9 (M), 10 (L), 18 (VL), or 25 (UL). The shader coefficients and hook bodies are
unchanged. Unlike mpv, the renderer does not use `WHEN` to skip the graph
based on viewport size: `passes=1`, `passes=2` and `passes=3` run the same
graph in sequence, producing native x2, x4 and x8 output respectively.

`scale=1.5|2|3|4` sets the final intermediate texture dimensions relative to
the input, rounded to the nearest pixel (ties up). If this differs from the
native CNN output, a bilinear pass resamples it into a separate texture.
Presentation then fits the texture to the widget with letterboxing and
preserves the input aspect ratio. Neither setting resizes the widget.

Before allocating textures, the renderer checks `GL_MAX_TEXTURE_SIZE` and,
when the driver exposes `GL_NVX_gpu_memory_info`, compares the estimated
texture footprint with the driver's estimate of currently available video
memory. OpenGL has no portable free-VRAM query. Without that extension, the
renderer relies on actual framebuffer allocation results instead of a fixed
memory budget. If the requested CNN runs do not fit, it tries fewer while keeping the
requested scale. If that also fails, it falls back to Qt raster scaling.
