using System.Net.Mail;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Licamvel.App.Models;
using Licamvel.App.Services;

namespace Licamvel.App.ViewModels;

public partial class LoginViewModel : ObservableObject
{
    // Rutas de Shell: ajústalas a las de tu AppShell.
    private const string RegisterRoute = "RegisterPage";
    private const string HomeRoute = "//CatalogoPage";

    private readonly IApiService _api;

    public LoginViewModel(IApiService api)
    {
        _api = api;
    }

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(LoginCommand))]
    private string _correo = string.Empty;

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(LoginCommand))]
    private string _password = string.Empty;

    [ObservableProperty]
    [NotifyCanExecuteChangedFor(nameof(LoginCommand))]
    [NotifyPropertyChangedFor(nameof(IsNotBusy))]
    private bool _isBusy;

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(HasError))]
    private string _errorMessage = string.Empty;

    public bool IsNotBusy => !IsBusy;
    public bool HasError => !string.IsNullOrWhiteSpace(ErrorMessage);

    private bool CanLogin() =>
        !IsBusy && !string.IsNullOrWhiteSpace(Correo) && !string.IsNullOrWhiteSpace(Password);

    [RelayCommand(CanExecute = nameof(CanLogin))]
    private async Task LoginAsync()
    {
        ErrorMessage = string.Empty;

        var correo = Correo.Trim();
        if (!MailAddress.TryCreate(correo, out _))
        {
            ErrorMessage = "Ingresa un correo electrónico válido.";
            return;
        }

        try
        {
            IsBusy = true;
            await _api.LoginAsync(correo, Password);
            Password = string.Empty;
            await Shell.Current.GoToAsync(HomeRoute);
        }
        catch (ApiException ex)
        {
            ErrorMessage = ex.Message;
        }
        catch (Exception ex)
        {
            // Errores de navegación u otros inesperados (ej. ruta no registrada).
            ErrorMessage = $"Ocurrió un error inesperado: {ex.Message}";
        }
        finally
        {
            IsBusy = false;
        }
    }


    [RelayCommand]
    private async Task LoginWithGoogleAsync()
    {
        ErrorMessage = string.Empty;

        try
        {
            IsBusy = true;

            // URL para iniciar OAuth con Google
            var authUrl = "https://accounts.google.com/o/oauth2/v2/auth" +
                        "?client_id=321475219574-nt1m7k982re0g9lrs5qthftdvf7cvv0.apps.googleusercontent.com" +
                        "&response_type=id_token" +
                        "&redirect_uri=com.companyname.licamvel.app://callback" +
                        "&scope=openid%20email%20profile" +
                        "&nonce=" + Guid.NewGuid().ToString("N");

            var authResult = await WebAuthenticator.Default.AuthenticateAsync(
                new Uri(authUrl),
                new Uri("com.companyname.licamvel.app://callback"));

            if (authResult?.Properties.TryGetValue("id_token", out var idToken) == true && !string.IsNullOrWhiteSpace(idToken))
            {
                await _api.LoginWithGoogleAsync(idToken);
                await Shell.Current.GoToAsync(HomeRoute);
            }
            else
            {
                ErrorMessage = "No se pudo obtener el token de autenticación de Google.";
            }
        }
        catch (TaskCanceledException)
        {
            // El usuario canceló o cerró la ventana de inicio de sesión
        }
        catch (ApiException ex)
        {
            ErrorMessage = ex.Message;
        }
        catch (Exception ex)
        {
            ErrorMessage = $"Error al autenticar con Google: {ex.Message}";
        }
        finally
        {
            IsBusy = false;
        }
    }

    [RelayCommand]
    private async Task GoToRegisterAsync()
    {
        ErrorMessage = string.Empty;

        try
        {
            await Shell.Current.GoToAsync(RegisterRoute);
        }
        catch (Exception)
        {
            ErrorMessage = "La pantalla de registro aún no está disponible.";
        }
    }
}