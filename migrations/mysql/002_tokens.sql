ALTER TABLE client_contexts DROP FOREIGN KEY fk_ctx_session;
ALTER TABLE auth_sessions MODIFY id VARCHAR(80) NOT NULL;
ALTER TABLE client_contexts MODIFY id VARCHAR(80) NOT NULL;
ALTER TABLE client_contexts MODIFY csrf_token VARCHAR(128) NOT NULL;
ALTER TABLE client_contexts MODIFY session_id VARCHAR(80) NULL;
ALTER TABLE client_contexts
    ADD CONSTRAINT fk_ctx_session FOREIGN KEY (session_id) REFERENCES auth_sessions(id) ON DELETE SET NULL;
