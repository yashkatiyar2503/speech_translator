# Speech Translator App

This application utilizes Azure AI Speech service to translate speech from one language to another.

## Setup Azure AI Speech Service

1. **Create Azure AI Speech Resource:**
   - Open the Azure portal at [https://portal.azure.com](https://portal.azure.com).
   - Sign in using the Microsoft account associated with your Azure subscription.
   - In the search field at the top, search for **Azure AI services** and press Enter.
   - Select **Create** under **Speech service** in the results.
   - Configure the resource:
     - **Subscription:** Select your Azure subscription.
     - **Resource group:** Choose or create a resource group.
     - **Region:** Choose any available region.
     - **Name:** Enter a unique name for your speech resource.
     - **Pricing tier:** Select **F0 (free)** or **S (standard)** if F is not available.
     - **Responsible AI Notice:** Agree.
   - Select **Review + create**, then select **Create** to provision the resource.
   - Wait for deployment to complete, and then go to the deployed resource.
   - View the **Keys and Endpoint** page. You will need the information on this page later.

2. **Update Configuration:**
   - Copy the `SPEECH_KEY` and `SPEECH_REGION` from the **Keys and Endpoint** page of your Azure AI Speech resource.
   - Open `.env` file in the project.
   - Replace `your_speech_resource_key` with your copied `SPEECH_KEY`.
   - Replace `your_speech_resource_region` with your copied `SPEECH_REGION`.

## Running the Application

1. **Install Dependencies:**
   - Ensure Python 3.x is installed on your system.
   - Install project dependencies using pip:
     ```
     pip install -r requirements.txt
     ```

2. **Run the Application:**
   - Execute the main application script:
     ```
     python -m App.main
     ```
   - The application will start and be accessible at `http://localhost:5000`.

## Contributing

Contributions are welcome! Here's how you can contribute:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature-name`).
3. Make your changes.
4. Commit your changes (`git commit -am 'Add some feature'`).
5. Push to the branch (`git push origin feature/your-feature-name`).
6. Create a new Pull Request.