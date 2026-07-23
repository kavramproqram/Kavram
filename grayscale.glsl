#version 330
in vec2 texcoord;
uniform sampler2D tex;
uniform float opacity;
vec4 default_post_processing(vec4 c);
vec4 window_shader() {
    vec2 sz = textureSize(tex, 0);
    vec4 c  = texture2D(tex, texcoord / sz, 0);
    float g = 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b;
    c = vec4(vec3(g) * opacity, c.a * opacity);
    return default_post_processing(c);
}