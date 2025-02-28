require("dotenv").config();
require("@nomiclabs/hardhat-waffle");
require("@nomiclabs/hardhat-ethers");

module.exports = {
  solidity: "0.8.0",
  networks: {
    sepolia: {
      url: "https://rpc.sepolia.org/", // Sepolia RPC URL
      accounts: [process.env.PRIVATE_KEY], // Your MetaMask private key (set in .env)
    },
  },
};