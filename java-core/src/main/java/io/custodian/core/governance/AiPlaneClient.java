package io.custodian.core.governance;

import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.Map;

/** Thin client to the Python AI plane's /assess endpoint. */
@Component
public class AiPlaneClient {

    private final RestClient client;

    public AiPlaneClient() {
        this.client = RestClient.builder()
                .baseUrl(System.getenv().getOrDefault("AI_PLANE_URL", "http://localhost:8000"))
                .build();
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> assess(String componentDescription) {
        return client.post()
                .uri("/assess")
                .body(Map.of("component_description", componentDescription))
                .retrieve()
                .body(Map.class);
    }
}
