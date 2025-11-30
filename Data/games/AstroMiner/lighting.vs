#version 330

// Input vertex attributes
in vec3 vertexPosition;
in vec2 vertexTexCoord;
in vec3 vertexNormal;
in vec4 vertexColor;

// Input uniform values
uniform mat4 mvp;
uniform mat4 matModel;
uniform mat4 matNormal;

// Output vertex attributes (to fragment shader)
out vec3 fragPosition;
out vec2 fragTexCoord;
out vec4 fragColor;
out vec3 fragNormal;

void main()
{
    // Calculate fragment position in world space
    fragPosition = vec3(matModel * vec4(vertexPosition, 1.0));

    // Calculate fragment normal (if non-uniform scale, use inverse-transpose)
    // For simple scaling, matNormal is sufficient
    fragNormal = normalize(vec3(matNormal * vec4(vertexNormal, 1.0)));

    // Pass texcoords and color
    fragTexCoord = vertexTexCoord;
    fragColor = vertexColor;

    // Calculate final vertex position
    gl_Position = mvp * vec4(vertexPosition, 1.0);
}

