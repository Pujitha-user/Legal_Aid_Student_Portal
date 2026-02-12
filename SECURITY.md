# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in this project, please report it by emailing the maintainers. **Do not create a public issue.**

## Security Best Practices

### Environment Variables
- Never commit `.env` files or any files containing sensitive credentials
- Use the provided `.env.example` as a template
- Rotate API keys and secrets regularly
- Use different credentials for development, staging, and production environments

### API Keys
- Store all API keys in environment variables
- Use the principle of least privilege for API keys
- Monitor API key usage for unusual activity
- Revoke and rotate keys if compromised

### Database Security
- Use strong passwords for database connections
- Enable MongoDB authentication in production
- Restrict database access by IP address when possible
- Regularly backup your database

### Dependencies
- Regularly update dependencies to patch security vulnerabilities
- Run `npm audit` or `pip check` to identify known vulnerabilities
- Review dependency licenses and sources

### System Configuration
- If using supervisor or similar process managers, ensure configuration files containing passwords are not committed to the repository
- Store supervisor passwords and other system credentials in environment variables or secure secrets management systems
- The file `/etc/supervisor/conf.d/supervisord_code_server.conf` should be kept secure and not be committed to version control

## Supported Versions

Currently supporting the latest version with security updates.
