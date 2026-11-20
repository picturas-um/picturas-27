module.exports = {
  testEnvironment: 'node',
  testMatch: ['<rootDir>/tests/functional/api/**/*.test.js'],
  reporters: ['default', ['jest-junit', { outputDirectory: 'tests/reports', outputName: 'jest-junit.xml' }]],
};
