export function getCategoryStyle(category) {
  const styles = {
    fir: 'category-fir',
    rti: 'category-rti',
    consumer: 'category-consumer',
    labour: 'category-labour',
    family: 'category-family',
    property: 'category-property',
    general: 'category-general'
  };
  return styles[category] || styles.general;
}

export function getCategoryLabel(category) {
  const labels = {
    fir: 'FIR / Police',
    rti: 'RTI',
    consumer: 'Consumer',
    labour: 'Labour',
    family: 'Family',
    property: 'Property',
    general: 'General'
  };
  return labels[category] || category;
}

export function getStatusStyle(status) {
  const styles = {
    open: 'status-open',
    assigned: 'status-assigned',
    closed: 'status-closed'
  };
  return styles[status] || styles.open;
}

export function getLanguageLabel(code) {
  const labels = {
    en: 'English',
    hi: 'हिंदी',
    te: 'తెలుగు'
  };
  return labels[code] || code;
}

export function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  });
}
