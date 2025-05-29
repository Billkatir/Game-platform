import React, { useState } from 'react';
import axios from 'axios';
import config from '../config';  // Import the configuration

function Register() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [userId, setUserId] = useState(''); // State to store the user_id
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(`${config.API_URL}/create_user`, {
        username: username,
        password: password,
      });
      setUserId(response.data.user_id); // Save user_id from response
      setErrorMessage(''); // Clear any previous errors
    } catch (error) {
      console.error('There was an error creating the user!', error);
      setErrorMessage('Error: Unable to create user');
      setUserId(''); // Clear any previous user_id
    }
  };

  return (
    <div className="flex items-center justify-center h-screen bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-lg w-full max-w-md">
        <h2 className="text-2xl font-bold text-center mb-6">Register</h2>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
              Username
            </label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <div className="mb-6">
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <button
            type="submit"
            className="w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 transition-colors duration-200"
          >
            Register
          </button>
        </form>
        {userId && (
          <div className="mt-6 bg-green-100 border border-green-400 text-green-700 p-4 rounded-md">
            <h3 className="font-semibold">Registration Successful!</h3>
            <p>
              User <strong>{username}</strong> was created successfully with User ID: <strong>{userId}</strong>.
            </p>
          </div>
        )}
        {errorMessage && (
          <p className="mt-4 text-red-500 text-center">{errorMessage}</p>
        )}
      </div>
    </div>
  );
}

export default Register;
