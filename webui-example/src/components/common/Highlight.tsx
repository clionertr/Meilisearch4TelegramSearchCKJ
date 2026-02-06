import React from 'react';
import DOMPurify from 'dompurify';

export const Highlight: React.FC<{html: string}> = ({ html }) => {
  const clean = DOMPurify.sanitize(html, { ALLOWED_TAGS: ['mark'] });
  return <span dangerouslySetInnerHTML={{ __html: clean }} />;
};
