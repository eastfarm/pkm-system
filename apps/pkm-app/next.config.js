// File: apps/pkm-app/next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: false, // Disable swc minification to help with debugging
  eslint: {
    ignoreDuringBuilds: true,
  },
  // Add log information during build
  webpack: (config, { isServer, dev }) => {
    // Force webpack to include detailed error information
    config.optimization.minimize = false;
    
    if (!isServer && !dev) {
      // More verbose webpack output for client builds
      config.infrastructureLogging = {
        level: 'verbose',
      };
    }
    
    return config;
  },
};

module.exports = nextConfig;