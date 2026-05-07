import React from 'react';

interface AdBannerProps {
  title: string;
  description: string;
  imageUrl: string;
  linkUrl: string;
  tag?: string;
  layout?: 'horizontal' | 'vertical';
}

const AdBanner: React.FC<AdBannerProps> = ({ title, description, imageUrl, linkUrl, tag, layout = 'horizontal' }) => {
  const isVertical = layout === 'vertical';

  return (
    <a 
      href={linkUrl} 
      target="_blank" 
      rel="noopener noreferrer" 
      style={{
        display: 'flex',
        flexDirection: isVertical ? 'column' : 'row',
        alignItems: isVertical ? 'flex-start' : 'center',
        background: 'var(--white)',
        border: '1px solid var(--gray-lt)',
        borderRadius: '12px',
        padding: '16px',
        textDecoration: 'none',
        color: 'inherit',
        marginBottom: '24px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.03)',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
        cursor: 'pointer',
        width: '100%',
        boxSizing: 'border-box'
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-2px)';
        e.currentTarget.style.boxShadow = '0 6px 16px rgba(0,0,0,0.06)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.03)';
      }}
    >
      {isVertical && (
        <div style={{ width: '100%', aspectRatio: '3/4', borderRadius: '8px', overflow: 'hidden', background: 'var(--gray-lt)', marginBottom: '16px' }}>
          <img src={imageUrl} alt="Advertisement" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        </div>
      )}
      
      <div style={{ flex: 1, paddingRight: isVertical ? '0' : '16px' }}>
        {tag && (
          <span style={{ 
            display: 'inline-block', 
            background: 'var(--accent-1-lt)', 
            color: 'var(--accent-1)', 
            fontSize: '9px', 
            fontFamily: 'Inter', 
            fontWeight: 600, 
            padding: '3px 8px', 
            borderRadius: '4px', 
            marginBottom: '8px',
            textTransform: 'uppercase',
            letterSpacing: '0.5px'
          }}>
            {tag}
          </span>
        )}
        <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--black)', marginBottom: '4px', lineHeight: 1.4 }}>
          {title}
        </div>
        <div style={{ fontSize: '11px', color: 'var(--gray-dark)', fontWeight: 300, lineHeight: 1.5 }}>
          {description}
        </div>
      </div>

      {!isVertical && (
        <div style={{ flexShrink: 0, width: '80px', height: '80px', borderRadius: '8px', overflow: 'hidden', background: 'var(--gray-lt)' }}>
          <img src={imageUrl} alt="Advertisement" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        </div>
      )}
    </a>
  );
};

export default AdBanner;
