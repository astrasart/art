require("@nomicfoundation/hardhat-chai-matchers");
require("@nomicfoundation/hardhat-ethers");

module.exports = {
  solidity: "0.8.28",
  networks: {
    sepolia: {
      url: "https://rpc.ankr.com/eth_sepolia", // Sepolia RPC URL
      accounts: ["b419426722b54e885c5e97a3ed36ba19e87f11df0a6826ddac1f68db1b8d8d92"], // Hardcoded MetaMask private key
    },
  },
};
