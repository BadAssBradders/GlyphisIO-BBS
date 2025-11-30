#version 330

// Input vertex attributes
in vec3 fragPosition;
in vec2 fragTexCoord;
in vec4 fragColor;
in vec3 fragNormal;

// Input uniform values
uniform sampler2D texture0;
uniform vec4 colDiffuse;

// Light uniforms
uniform vec3 lightPos;
uniform vec3 lightColor;
uniform vec3 lightPos2;
uniform vec3 lightColor2;
uniform vec3 lightPos3;
uniform vec3 lightColor3;
uniform vec3 lightPos4;
uniform vec3 lightColor4;

// Camera Spot Light (Light 5)
uniform vec3 lightPos5;
uniform vec3 lightDir5;
uniform vec3 lightColor5;
uniform float lightCutoff5; // Cosine of cutoff angle

uniform vec3 ambientColor;
uniform vec3 viewPos;

// Output fragment color
out vec4 finalColor;

void main()
{
    // Texture sample
    vec4 texelColor = texture(texture0, fragTexCoord);
    vec4 baseColor = texelColor * colDiffuse * fragColor;
    vec3 ambient = ambientColor * baseColor.rgb;
    
    vec3 norm = normalize(fragNormal);
    vec3 viewDir = normalize(viewPos - fragPosition);

    // Light 1 (Top)
    vec3 lightDir = normalize(lightPos - fragPosition);
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diff * lightColor * baseColor.rgb;
    
    // Specular 1
    vec3 halfwayDir = normalize(lightDir + viewDir);
    float spec = pow(max(dot(norm, halfwayDir), 0.0), 16.0);
    vec3 specular = vec3(0.3) * spec;

    // Light 2 (Left)
    vec3 lDir2 = normalize(lightPos2 - fragPosition);
    float diff2 = max(dot(norm, lDir2), 0.0);
    vec3 diffuse2 = diff2 * lightColor2 * baseColor.rgb;

    // Light 3 (Top Left Spot)
    vec3 lDir3 = normalize(lightPos3 - fragPosition);
    float diff3 = max(dot(norm, lDir3), 0.0);
    vec3 diffuse3 = diff3 * lightColor3 * baseColor.rgb;
    // Specular 3
    vec3 hDir3 = normalize(lDir3 + viewDir);
    float spec3 = pow(max(dot(norm, hDir3), 0.0), 16.0);
    vec3 specular3 = vec3(0.8) * spec3;

    // Light 4 (Top Down Blue)
    vec3 lDir4 = normalize(lightPos4 - fragPosition);
    float diff4 = max(dot(norm, lDir4), 0.0);
    vec3 diffuse4 = diff4 * lightColor4 * baseColor.rgb;

    // Light 5 (Camera Spot Light)
    vec3 lDir5 = normalize(lightPos5 - fragPosition);
    float theta = dot(lDir5, normalize(-lightDir5));
    vec3 diffuse5 = vec3(0.0);
    vec3 specular5 = vec3(0.0);
    
    if (theta > lightCutoff5) 
    {
        // Soft edge intensity
        // For simplicity just hard cutoff or linear fade could be added
        float diff5 = max(dot(norm, lDir5), 0.0);
        diffuse5 = diff5 * lightColor5 * baseColor.rgb;
        
        // Specular 5
        vec3 hDir5 = normalize(lDir5 + viewDir);
        float sp5 = pow(max(dot(norm, hDir5), 0.0), 16.0);
        specular5 = vec3(0.5) * sp5; 
    }

    // Combine
    vec3 result = ambient + diffuse + diffuse2 + diffuse3 + diffuse4 + diffuse5 + specular + specular3 + specular5;
    
    finalColor = vec4(result, baseColor.a);
}
